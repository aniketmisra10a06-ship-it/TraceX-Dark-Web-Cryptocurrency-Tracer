"""Markdown investigation report with embedded Mermaid diagrams (renders on GitHub)."""
from __future__ import annotations

from pathlib import Path

from ..analysis import Investigation
from ..labels import CATEGORIES
from ..utils import iso, short
from . import mermaid

BADGE = {"low": "🟢", "medium": "🟡", "high": "🟠", "severe": "🔴"}
SEV = {"info": "ℹ️", "low": "🟢", "medium": "🟡", "high": "🟠", "critical": "🔴"}


def _cell(s) -> str:
    return str(s).replace("|", "\\|").replace("\n", " ")


def build(inv: Investigation) -> str:
    s, sym = inv.stats, inv.symbol
    L = []
    L.append("# TraceX Investigation Report\n")
    L.append(f"> Generated {inv.meta['generated']} · chain **{inv.chain.upper()}** · TraceX v{inv.meta['version']}  ")
    L.append("> ⚠️ Heuristic analysis of public ledger data. Findings are investigative leads, **not proof** of identity or wrongdoing.\n")
    L.append("## 1. Summary\n")
    L.append("| Metric | Value |\n|---|---|")
    for k, v in [("Seeds", ", ".join(f"`{short(x, 24)}`" for x in inv.seeds)), ("Addresses", s["addresses"]),
                 ("Transactions", s["transactions"]), ("Edges", s["edges"]), ("Labeled addresses", s["labeled_addresses"]),
                 ("Clusters", s["clusters"]), ("CoinJoins", s["coinjoins"]), ("Peel chains", s["peel_chains"]),
                 (f"Total volume ({sym})", f"{s['total_volume']:.6f}"), (f"Fees ({sym})", f"{s['total_fees']:.6f}"),
                 ("Period", f"{s['first_tx']} → {s['last_tx']}"), ("Tainted addresses", s["tainted_addresses"])]:
        L.append(f"| {k} | {v} |")
    L.append("\n## 2. Risk assessment\n")
    for a, r in inv.risk.items():
        L.append(f"### {BADGE[r.level]} `{short(a, 24)}` — **{r.score}/100 ({r.level})**\n")
        L.append("| Risk factor | Detail | Contribution |\n|---|---|---|")
        for f in r.factors:
            L.append(f"| {_cell(f['factor'])} | {_cell(f['detail'])} | {f['contribution']:.2f} |")
        if not r.factors:
            L.append("| _none_ | | |")
        L.append("")
    L.append("## 3. Findings\n")
    L.append("| Severity | Type | Finding | Detail |\n|---|---|---|---|")
    for f in inv.heur.findings:
        L.append(f"| {SEV[f.severity]} {f.severity} | {f.kind} | {_cell(f.title)} | {_cell(f.detail)} |")
    L.append("\n## 4. Money-flow diagram\n")
    L.append("```mermaid\n" + mermaid.flowchart(inv) + "\n```\n")
    L.append("## 5. Category flow (Sankey, by hop)\n")
    sk = mermaid.sankey(inv)
    L.append("```mermaid\n" + sk + "\n```\n")
    L.append("## 6. Chronological sequence\n")
    L.append("```mermaid\n" + mermaid.sequence(inv) + "\n```\n")
    for i, pc in enumerate(inv.heur.peel_chains):
        L.append(f"## 7.{i + 1} Peel chain ({len(pc.txids)} hops)\n")
        L.append("```mermaid\n" + mermaid.peel_chain(inv, i) + "\n```\n")
    cl = mermaid.clusters(inv)
    if cl:
        L.append("## 8. Address clusters\n")
        L.append("```mermaid\n" + cl + "\n```\n")
    L.append("## 9. Labeled entities in scope\n")
    L.append("| Address | Entity | Category | Confidence | Source | Taint |\n|---|---|---|---|---|---|")
    for a, n in inv.graph.nodes.items():
        p = inv.labels.primary(a)
        if p:
            L.append(f"| `{short(a, 24)}` | {_cell(p.name)} | {CATEGORIES[p.category]['title']} | {p.confidence:.0%} | "
                     f"{_cell(p.source)} | {inv.taint.get(a, 0):.0%} |")
    L.append("\n## 10. Largest transactions\n")
    L.append(f"| Time | Txid | In→Out | Total ({sym}) | Flags |\n|---|---|---|---|---|")
    d = inv.to_dict()["transactions"]
    for t in sorted(d, key=lambda x: -x["total"])[:15]:
        L.append(f"| {iso(t['ts'])} | `{t['txid'][:16]}…` | {t['n_in']}→{t['n_out']} | {t['total']:.6f} | {', '.join(t['flags'])} |")
    L.append("\n## 11. Methodology & limitations\n")
    L.append("- Attribution comes **only** from the label files you supplied; unlabeled ≠ innocent.\n"
             "- Common-input clustering is excluded for CoinJoins but can still over-merge (e.g., PayJoin).\n"
             "- Change detection, peel chains and taint are probabilistic. Haircut taint is proportional; poison taint is worst-case.\n"
             "- Traces are bounded by depth / transaction caps; see `manifest.json` for exact parameters.\n"
             "- Do not treat output as legal evidence without independent corroboration and chain-of-custody review.\n")
    return "\n".join(L)


def write(inv: Investigation, path: Path) -> None:
    path.write_text(build(inv), encoding="utf-8")
