"""Self-contained interactive HTML report (no CDN, no external requests, strict CSP)."""
from __future__ import annotations

import json
from pathlib import Path

from ..analysis import Investigation

TEMPLATE = Path(__file__).resolve().parent.parent / "templates" / "report.html"


def build(inv: Investigation) -> str:
    data = json.dumps(inv.to_dict(), ensure_ascii=False)
    # keep embedded JSON from terminating the script block or opening HTML comments
    for ch, esc in (("<", "\\u003c"), (">", "\\u003e"), ("&", "\\u0026"), (" ", "\\u2028"), (" ", "\\u2029")):
        data = data.replace(ch, esc)
    return TEMPLATE.read_text(encoding="utf-8").replace("__DATA__", data, 1)


def write(inv: Investigation, path: Path) -> None:
    path.write_text(build(inv), encoding="utf-8")
