"""Verification gate: tokenize and decode EVERY record of EVERY TEXT.DKI in a library.

usage: uv run python scripts/dki_gate.py "L:/Multimedia Files/Written Word/Digitale Bibliothek" [VOLUME]

A record passes when its token stream ends exactly at the record boundary with the
end-of-record token 0x03 and decode_record() succeeds. Exit code 1 if any record fails.
"""

import collections
import sys
from pathlib import Path

from directmedia_mcp.dki_text import OP_END, DkiFormatError, TextDki, find_text_dki, iter_tokens


def check_record(dki: TextDki, k: int) -> str | None:
    rec = dki.raw_record(k)
    try:
        last_op, last_end = None, dki.header_size
        for op, i, size in iter_tokens(rec, dki.header_size):
            last_op, last_end = op, i + size
            if op == OP_END:
                break
        if last_op != OP_END or last_end != len(rec):
            return "no end token at record boundary"
        dki.decode_record(k)
    except DkiFormatError as exc:
        return str(exc).split(" at ")[0]
    return None


def main() -> int:
    root = Path(sys.argv[1])
    only = sys.argv[2] if len(sys.argv) > 2 else None
    total = passed = 0
    for vol in sorted(p for p in root.iterdir() if p.is_dir()):
        if only and vol.name.lower() != only.lower():
            continue
        path = find_text_dki(vol)
        if path is None:
            continue
        fails: collections.Counter[str] = collections.Counter()
        with TextDki(path) as dki:
            for k in range(dki.count):
                why = check_record(dki, k)
                if why:
                    fails[why] += 1
            ok = dki.count - sum(fails.values())
            total += dki.count
            passed += ok
            status = "OK " if not fails else "BAD"
            print(f"{status} {vol.name:8} {dki.family}v{dki.version}  {ok}/{dki.count}  {dict(fails) if fails else ''}")
    print(f"TOTAL {passed}/{total} records decode exactly")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
