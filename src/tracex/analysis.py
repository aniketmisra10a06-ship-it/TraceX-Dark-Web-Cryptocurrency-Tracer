"""Run every analysis stage and assemble an `Investigation` that all reporters consume."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from . import __version__
from .graph import TxGraph
from .heuristics import HeuristicResults, run_heuristics
from .labels import CATEGORIES, LabelDB
from .models import SYMBOL, to_coin
from .risk import RiskResult, score_address
from .taint import propagate_taint
from .utils import iso, short, utcnow_iso


@dataclass
class Investigation:
    graph: TxGraph
    labels: LabelDB
    heur: HeuristicResults
    seeds: List[str]
    taint: Dict[str, float]
    risk: Dict[str, RiskResult]
    meta: Dict
    stats: Dict = field(default_factory=dict)

    @property
    def chain(self) -> str:
        return self.graph.chain

    @property
    def symbol(self) -> str:
        return SYMBOL.get(self.chain, self.chain.upper())

    def coin(self, v: float) -> float:
        return to_coin(v, self.chain)

    def category(self, addr: str) -> str:
        return self.labels.category(addr)

    def display_name(self, addr: str) -> str:
        p = self.labels.primary(addr)
        return p.name if p else short(addr)

    # ------------------------------------------------------------ flows
    def category_flows(self) -> Dict[str, Dict[str, float]]:
        flows: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
        for (s, d), e in self.graph.edges.items():
            flows[self.category(s)][self.category(d)] += self.coin(e.value)
        return {k: dict(v) for k, v in flows.items()}

    # ------------------------------------------------------------ serialisation
    def to_dict(self) -> Dict:
        g = self.graph
        nodes = []
        for a, n in g.nodes.items():
            p = self.labels.primary(a)
            nodes.append({
                "id": a, "short": short(a), "name": p.name if p else "",
                "category": p.category if p else "unlabeled",
                "labels": [l.to_dict() for l in n.labels],
                "received": self.coin(n.received), "sent": self.coin(n.sent), "tx_count": n.tx_count,
                "first_seen": n.first_seen, "last_seen": n.last_seen, "depth": n.depth or 0,
                "cluster": n.cluster, "taint": self.taint.get(a, 0.0), "seed": n.is_seed,
                "tags": sorted(n.tags),
            })
        edges = [{"s": e.src, "t": e.dst, "value": self.coin(e.value), "count": e.count,
                  "txids": e.txids[:25], "first": e.first, "last": e.last} for e in g.edges.values()]
        cj, peel_tx = self.heur.coinjoins, {t for pc in self.heur.peel_chains for t in pc.txids}
        txs = []
        for t in g.txs_sorted():
            flags = []
            if t.txid in cj:
                flags.append("coinjoin")
            if t.txid in peel_tx:
                flags.append("peel")
            if t.coinbase:
                flags.append("coinbase")
            txs.append({
                "txid": t.txid, "ts": t.timestamp, "height": t.block_height, "fee": self.coin(t.fee),
                "n_in": len(t.inputs), "n_out": len(t.outputs), "total": self.coin(t.total_out), "flags": flags,
                "inputs": [{"a": l.address, "v": self.coin(l.value)} for l in t.inputs[:30]],
                "outputs": [{"a": l.address, "v": self.coin(l.value)} for l in t.outputs[:30]],
            })
        return {
            "meta": self.meta, "stats": self.stats, "symbol": self.symbol, "seeds": self.seeds,
            "categories": {k: {"color": v["color"], "title": v["title"], "weight": v["weight"]}
                           for k, v in CATEGORIES.items()},
            "nodes": nodes, "edges": edges, "transactions": txs,
            "findings": [f.to_dict() for f in self.heur.findings],
            "clusters": [{"id": c.id, "members": c.members, "name": c.name, "category": c.category,
                          "evidence": c.evidence_txids} for c in self.heur.clusters],
            "peel_chains": [{"txids": p.txids, "peel_addresses": p.peel_addresses,
                             "change_addresses": p.change_addresses, "total_peeled": p.total_peeled}
                            for p in self.heur.peel_chains],
            "risk": {k: v.to_dict() for k, v in self.risk.items()},
            "category_flows": self.category_flows(),
            "labels_loaded": len(self.labels), "label_warnings": self.labels.warnings[:20],
        }


def investigate(graph: TxGraph, labels: LabelDB, seeds: List[str], meta: Optional[Dict] = None,
                taint_mode: str = "haircut", taint_sources: Optional[List[str]] = None,
                taint_threshold: float = 0.7) -> Investigation:
    heur = run_heuristics(graph, labels)
    sources: Dict[str, float] = {}
    for a in graph.nodes:
        p = labels.primary(a)
        if p and p.weight >= taint_threshold:
            sources[a] = 1.0
    for a in taint_sources or []:
        sources[a] = 1.0
    taint = propagate_taint(graph, sources, taint_mode) if sources else {}
    for a, t in taint.items():
        if a in graph.nodes:
            graph.nodes[a].taint = t
    risk = {s: score_address(graph, labels, s, heur, taint) for s in seeds if s in graph.nodes}

    txs = graph.txs_sorted()
    stamps = [t.timestamp for t in txs if t.timestamp]
    chain = graph.chain
    stats = {
        "addresses": len(graph.nodes), "edges": len(graph.edges), "transactions": len(graph.txs),
        "labeled_addresses": sum(1 for a in graph.nodes if labels.get(a)),
        "clusters": len(heur.clusters), "coinjoins": len(heur.coinjoins), "peel_chains": len(heur.peel_chains),
        "findings": len(heur.findings),
        "total_volume": to_coin(sum(t.total_out for t in txs), chain),
        "total_fees": to_coin(sum(t.fee for t in txs), chain),
        "first_tx": iso(min(stamps)) if stamps else "", "last_tx": iso(max(stamps)) if stamps else "",
        "tainted_addresses": len(taint),
        "max_depth": max((abs(n.depth or 0) for n in graph.nodes.values()), default=0),
    }
    m = {"tool": "TraceX", "version": __version__, "generated": utcnow_iso(), "chain": chain,
         "taint_mode": taint_mode, **(meta or {})}
    return Investigation(graph, labels, heur, seeds, taint, risk, m, stats)
