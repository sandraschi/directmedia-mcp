"""Hermetic tests for the TextGrid client and the textgrid MCP tool (no network)."""

import asyncio

import httpx
import pytest

from directmedia_mcp import textgrid as tg

SEARCH_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<tgs:response xmlns="http://textgrid.info/namespaces/metadata/core/2010"
  xmlns:tgs="http://www.textgrid.info/namespaces/middleware/tgsearch" hits="61" limit="1">
<tgs:result author="Goethe, Johann Wolfgang von" score="12.8">
<object><generic><provided><title>Faust. Eine Tragödie</title>
<format>text/tg.edition+tg.aggregation+xml</format></provided>
<generated><textgridUri extRef="">textgrid:11d4b.0</textgridUri>
<project id="TGPR-372fe6dc-57f2-6cd4-01b5-2c4bbefcfd3c">Digitale Bibliothek</project></generated></generic>
<edition><agent role="author" id="">Goethe, Johann Wolfgang von</agent>
<source><bibliographicCitation><editionTitle>Goethes Werke. Hamburger Ausgabe</editionTitle>
<dateOfPublication date="1948"></dateOfPublication></bibliographicCitation></source>
<language>deu</language></edition></object>
</tgs:result>
</tgs:response>"""

FAUST = "Johann Wolfgang Goethe\nFaust. Eine Tragödie\nZueignung.\nIhr naht euch wieder, schwankende Gestalten,\n"


def make_client(seen: list[httpx.Request]) -> tg.TextGridClient:
    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        path = request.url.path
        if path.endswith("/search"):
            return httpx.Response(200, text=SEARCH_XML)
        if "/aggregator/text/" in path:
            return httpx.Response(200, content=FAUST.encode("utf-8"), headers={"content-type": "text/plain"})
        if "/aggregator/epub/" in path:
            return httpx.Response(200, content=b"PK\x03\x04fake-epub")
        return httpx.Response(404)

    return tg.TextGridClient(transport=httpx.MockTransport(handler))


def run(coro):
    return asyncio.run(coro)


def test_parse_search_response():
    hits, eds = tg.parse_search_response(SEARCH_XML)
    assert hits == 61
    assert eds == [
        tg.Edition(
            uri="textgrid:11d4b.0",
            title="Faust. Eine Tragödie",
            author="Goethe, Johann Wolfgang von",
            edition_title="Goethes Werke. Hamburger Ausgabe",
            date="1948",
            language="deu",
        )
    ]


def test_search_filters_to_digibib_project():
    seen: list[httpx.Request] = []
    client = make_client(seen)
    result = run(client.search("Faust", author="Goethe", limit=1))
    run(client.aclose())
    filters = seen[0].url.params.get_list("filter")
    assert f"project.id:{tg.DIGIBIB_PROJECT_ID}" in filters
    assert f"format:{tg.EDITION_FORMAT}" in filters
    assert seen[0].url.params["q"] == 'Faust AND edition.agent.value:"Goethe"'
    assert result["total_hits"] == 61
    assert result["next_start"] == 1


def test_get_text_pages():
    seen: list[httpx.Request] = []
    client = make_client(seen)
    page = run(client.get_text("11d4b.0", offset=0, max_chars=10))
    rest = run(client.get_text("textgrid:11d4b.0", offset=page["next_offset"], max_chars=10_000))
    run(client.aclose())
    assert page["uri"] == "textgrid:11d4b.0"
    assert page["text"] + rest["text"] == FAUST
    assert rest["next_offset"] is None
    assert "Tragödie" in rest["text"]


def test_export_epub_writes_file(tmp_path):
    client = make_client([])
    result = run(client.export_epub("textgrid:11d4b.0", str(tmp_path)))
    run(client.aclose())
    assert (tmp_path / "textgrid_11d4b.0.epub").read_bytes().startswith(b"PK")
    assert result["bytes"] == len(b"PK\x03\x04fake-epub")


@pytest.mark.parametrize("bad", ["http://evil/x", "textgrid:../../etc", "", "textgrid:ABC.0"])
def test_normalize_uri_rejects_non_uris(bad):
    with pytest.raises(ValueError):
        tg.normalize_uri(bad)


def test_tool_reports_missing_params():
    from directmedia_mcp.server import textgrid

    out = run(textgrid(operation="get_text"))
    assert out["success"] is False
    assert "uri" in out["error"]
    assert out["suggestions"]
