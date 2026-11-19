"""Report writers. `write_all` produces every requested format plus a SHA-256 manifest."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, List

from ..analysis import Investigation
from ..utils import sha256_file
from . import exporters, html_report, markdown, mermaid

ALL_FORMATS = ["html", "md", "json", "csv", "graphml", "gexf", "dot", "mermaid", "cypher"]


def write_all(inv: Investigation, outdir: str, formats: Iterable[str] = ("all",), extra_meta=None) -> List[Path]:
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    fmts = ALL_FORMATS if "all" in formats else list(formats)
    written: List[Path] = []

    def mark(p: Path):
        written.append(p)

    if "html" in fmts:
        html_report.write(inv, out / "report.html"); mark(out / "report.html")
    if "md" in fmts:
        markdown.write(inv, out / "report.md"); mark(out / "report.md")
    if "json" in fmts:
        exporters.write_json(inv, out / "graph.json"); mark(out / "graph.json")
    if "csv" in fmts:
        exporters.write_csv(inv, out)
        written += [out / f for f in ("nodes.csv", "edges.csv", "transactions.csv", "findings.csv")]
    if "graphml" in fmts:
        exporters.write_graphml(inv, out / "graph.graphml"); mark(out / "graph.graphml")
    if "gexf" in fmts:
        exporters.write_gexf(inv, out / "graph.gexf"); mark(out / "graph.gexf")
    if "dot" in fmts:
        exporters.write_dot(inv, out / "graph.dot"); mark(out / "graph.dot")
    if "cypher" in fmts:
        exporters.write_cypher(inv, out / "neo4j.cypher"); mark(out / "neo4j.cypher")
    if "mermaid" in fmts:
        parts = {"flow.mmd": mermaid.flowchart(inv), "sankey.mmd": mermaid.sankey(inv),
                 "sequence.mmd": mermaid.sequence(inv), "peel_chain.mmd": mermaid.peel_chain(inv),
                 "clusters.mmd": mermaid.clusters(inv)}
        for name, text in parts.items():
            if text:
                (out / name).write_text(text, encoding="utf-8"); mark(out / name)

    manifest = {
        "tool": inv.meta["tool"], "version": inv.meta["version"], "generated": inv.meta["generated"],
        "parameters": {k: v for k, v in inv.meta.items() if k not in ("tool", "version", "generated")},
        "seeds": inv.seeds, "stats": inv.stats,
        "files": {p.name: sha256_file(p) for p in written},
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    written.append(out / "manifest.json")
    return written
