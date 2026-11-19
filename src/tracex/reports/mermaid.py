"""Mermaid diagram generators (render natively on GitHub, GitLab, Obsidian, mermaid.live)."""
from __future__ import annotations

import re
from typing import Dict, List, Set

from ..analysis import Investigation
from ..labels import CATEGORIES
from ..utils import iso

_BAD = re.compile(r'[\"\[\]\(\)\{\}<>|;#&,\n\r`]')


def esc(s: str) -> str:
    return _BAD.sub(" ", str(s)).strip()


def _select(inv: Investigation, limit: int) -> List[str]:
    g = inv.graph

    def prio(a):
        n = g.nodes[a]
        return (-(n.is_seed), -(bool(inv.labels.get(a))), -(n.received + n.sent))
    return sorted(g.nodes, key=prio)[:limit]


def flowchart(inv: Investigation, max_nodes: int = 40, direction: str = "LR") -> str:
    keep = _select(inv, max_nodes)
    ks: Set[str] = set(keep)
    ids = {a: f"n{i}" for i, a in enumerate(keep)}
    out = [f"flowchart {direction}"]
    for a in keep:
        n = inv.graph.nodes[a]
        name = esc(inv.display_name(a))
        extra = f"<br/>{inv.coin(n.received):.4g} {inv.symbol} in"
        if n.taint >= 0.05:
            extra += f"<br/>taint {n.taint:.0%}"
        shape = ('(("', '"))') if n.is_seed else ('["', '"]')
        out.append(f"  {ids[a]}{shape[0]}{name}{extra}{shape[1]}:::{inv.category(a)}")
    for (s, t), e in inv.graph.edges.items():
        if s in ks and t in ks:
            out.append(f"  {ids[s]} -->|{inv.coin(e.value):.4g} {inv.symbol}| {ids[t]}")
    for cat, v in CATEGORIES.items():
        out.append(f"  classDef {cat} fill:{v['color']}33,stroke:{v['color']},stroke-width:2px,color:#111;")
    if len(inv.graph.nodes) > max_nodes:
        out.insert(1, f"  %% showing {max_nodes} of {len(inv.graph.nodes)} nodes (seeds, labeled, highest volume)")
    return "\n".join(out)


def sankey(inv: Investigation) -> str:
    """Hop-layered category flow (acyclic by construction: only edges that go to a deeper hop)."""
    agg: Dict[tuple, float] = {}
    nodes = inv.graph.nodes
    for (s, t), e in inv.graph.edges.items():
        ds, dt = nodes[s].depth or 0, nodes[t].depth or 0
        if not dt > ds:
            continue
        key = (f"{CATEGORIES[inv.category(s)]['title']} h{ds}", f"{CATEGORIES[inv.category(t)]['title']} h{dt}")
        agg[key] = agg.get(key, 0.0) + inv.coin(e.value)
    lines = ["sankey-beta", ""]
    for (a, b), v in sorted(agg.items(), key=lambda kv: -kv[1]):
        if v > 0:
            lines.append(f"{esc(a)},{esc(b)},{v:.6f}")
    return "\n".join(lines)


def sequence(inv: Investigation, max_msgs: int = 25, max_actors: int = 9) -> str:
    keep = _select(inv, max_actors)
    ks = set(keep)
    ids = {a: f"A{i}" for i, a in enumerate(keep)}
    out = ["sequenceDiagram", "  autonumber"]
    for a in keep:
        out.append(f"  participant {ids[a]} as {esc(inv.display_name(a))}")
    rows = sorted(((e.first or 0, s, t, e) for (s, t), e in inv.graph.edges.items() if s in ks and t in ks))
    for ts, s, t, e in rows[:max_msgs]:
        out.append(f"  {ids[s]}->>{ids[t]}: {inv.coin(e.value):.4g} {inv.symbol} ({esc(iso(ts)[:10])})")
    return "\n".join(out)


def peel_chain(inv: Investigation, idx: int = 0) -> str:
    if idx >= len(inv.heur.peel_chains):
        return ""
    pc = inv.heur.peel_chains[idx]
    out = ["flowchart LR"]
    for i, txid in enumerate(pc.txids):
        tx = inv.graph.txs[txid]
        out.append(f'  T{i}["tx {txid[:8]}<br/>{inv.coin(tx.total_in):.4g} {inv.symbol}"]')
        out.append(f'  P{i}(["{esc(inv.display_name(pc.peel_addresses[i]))}<br/>peel"]):::{inv.category(pc.peel_addresses[i])}')
        out.append(f"  T{i} -->|peel| P{i}")
        if i + 1 < len(pc.txids):
            out.append(f"  T{i} ==>|change| T{i + 1}")
    for cat, v in CATEGORIES.items():
        out.append(f"  classDef {cat} fill:{v['color']}33,stroke:{v['color']};")
    return "\n".join(out)


def clusters(inv: Investigation, max_clusters: int = 6) -> str:
    out = ["flowchart TB"]
    for c in inv.heur.clusters[:max_clusters]:
        out.append(f'  subgraph C{c.id}["Cluster {c.id}: {esc(c.name or "unattributed")}"]')
        for i, m in enumerate(c.members[:12]):
            out.append(f'    C{c.id}_{i}["{esc(inv.display_name(m))}"]:::{inv.category(m)}')
        out.append("  end")
    for cat, v in CATEGORIES.items():
        out.append(f"  classDef {cat} fill:{v['color']}33,stroke:{v['color']};")
    return "\n".join(out) if len(out) > 1 else ""
