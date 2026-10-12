"""TextGrid Repository client for the public-domain Digitale Bibliothek corpus.

The zeno.org / Digitale Bibliothek texts are published by TextGrid as TEI. Annotated
data and metadata: CC-BY 3.0 DE (credit "TextGrid"); the underlying plain texts are
public domain. This client talks to the public, unauthenticated endpoints only:

- tgsearch-public: full-text / metadata search
- aggregator: plain-text and EPUB export of an edition
"""

import re
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import httpx
from defusedxml.ElementTree import fromstring as safe_fromstring

SEARCH_URL = "https://textgridlab.org/1.0/tgsearch-public/search"
AGGREGATOR_URL = "https://textgridlab.org/1.0/aggregator"
DIGIBIB_PROJECT_ID = "TGPR-372fe6dc-57f2-6cd4-01b5-2c4bbefcfd3c"
EDITION_FORMAT = "text/tg.edition+tg.aggregation+xml"
ATTRIBUTION = "TextGrid (Digitale Bibliothek, CC-BY 3.0 DE annotations; texts public domain)"

_NS = {
    "tg": "http://textgrid.info/namespaces/metadata/core/2010",
    "tgs": "http://www.textgrid.info/namespaces/middleware/tgsearch",
}
_URI_RE = re.compile(r"^textgrid:[a-z0-9]+(\.[0-9]+)?$")


@dataclass
class Edition:
    """One edition (book-level object) from the Digitale Bibliothek project."""

    uri: str
    title: str
    author: str
    edition_title: str
    date: str
    language: str


def normalize_uri(uri: str) -> str:
    """Accept 'textgrid:abcd.0' or bare 'abcd.0'; reject anything else (no URL injection)."""
    uri = uri.strip()
    if not uri.startswith("textgrid:"):
        uri = f"textgrid:{uri}"
    if not _URI_RE.match(uri):
        raise ValueError(f"Not a TextGrid URI: {uri!r} (expected e.g. 'textgrid:11d4b.0')")
    return uri


def _text(el: ET.Element | None, path: str) -> str:
    if el is None:
        return ""
    found = el.find(path, _NS)
    return (found.text or "").strip() if found is not None else ""


def parse_search_response(xml_text: str) -> tuple[int, list[Edition]]:
    """Parse a tgsearch XML response into (total_hits, editions)."""
    root = safe_fromstring(xml_text)
    hits = int(root.get("hits", "0"))
    editions = []
    for result in root.findall("tgs:result", _NS):
        obj = result.find("tg:object", _NS)
        edition = obj.find("tg:edition", _NS) if obj is not None else None
        date_el = edition.find(".//tg:dateOfPublication", _NS) if edition is not None else None
        date = ""
        if date_el is not None:
            date = date_el.get("date") or date_el.get("notBefore") or (date_el.text or "").strip()
        editions.append(
            Edition(
                uri=_text(obj, "tg:generic/tg:generated/tg:textgridUri"),
                title=_text(obj, "tg:generic/tg:provided/tg:title"),
                author=result.get("author", "") or _text(edition, "tg:agent"),
                edition_title=_text(edition, ".//tg:editionTitle"),
                date=date,
                language=_text(edition, "tg:language"),
            )
        )
    return hits, editions


class TextGridClient:
    """Thin async client; one httpx.AsyncClient per instance."""

    def __init__(self, timeout: float = 60.0, transport: httpx.AsyncBaseTransport | None = None):
        self._client = httpx.AsyncClient(timeout=timeout, transport=transport, follow_redirects=True)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def search(self, query: str, author: str | None = None, limit: int = 20, start: int = 0) -> dict[str, Any]:
        """Search editions in the Digitale Bibliothek project."""
        q = query.strip() or "*"
        if author:
            q = f'{q} AND edition.agent.value:"{author.strip()}"'
        params = [
            ("q", q),
            ("filter", f"project.id:{DIGIBIB_PROJECT_ID}"),
            ("filter", f"format:{EDITION_FORMAT}"),
            ("limit", str(limit)),
            ("start", str(start)),
        ]
        resp = await self._client.get(SEARCH_URL, params=params)
        resp.raise_for_status()
        hits, editions = parse_search_response(resp.text)
        return {
            "total_hits": hits,
            "start": start,
            "returned": len(editions),
            "next_start": start + len(editions) if start + len(editions) < hits else None,
            "editions": [asdict(e) for e in editions],
        }

    async def get_text(self, uri: str, offset: int = 0, max_chars: int = 20000) -> dict[str, Any]:
        """Fetch the plain text of an edition and return one page of it."""
        uri = normalize_uri(uri)
        resp = await self._client.get(f"{AGGREGATOR_URL}/text/{uri}")
        resp.raise_for_status()
        resp.encoding = "utf-8"
        text = resp.text
        chunk = text[offset : offset + max_chars]
        end = offset + len(chunk)
        return {
            "uri": uri,
            "total_chars": len(text),
            "offset": offset,
            "returned_chars": len(chunk),
            "next_offset": end if end < len(text) else None,
            "text": chunk,
            "attribution": ATTRIBUTION,
        }

    async def export_epub(self, uri: str, output_dir: str) -> dict[str, Any]:
        """Download TextGrid's own EPUB rendering of an edition to output_dir."""
        uri = normalize_uri(uri)
        resp = await self._client.get(f"{AGGREGATOR_URL}/epub/{uri}")
        resp.raise_for_status()
        if not resp.content.startswith(b"PK"):
            raise ValueError(
                f"Aggregator did not return an EPUB for {uri} (content-type {resp.headers.get('content-type')})"
            )
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        path = out / f"{uri.replace(':', '_')}.epub"
        path.write_bytes(resp.content)
        return {"uri": uri, "path": str(path), "bytes": len(resp.content), "attribution": ATTRIBUTION}
