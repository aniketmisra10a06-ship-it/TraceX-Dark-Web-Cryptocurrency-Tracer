"""Explainable 0-100 risk score (noisy-OR over independent risk factors)."""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Dict, List

from .graph import TxGraph
from .heuristics import HeuristicResults
from .labels import CATEGORIES, LabelDB

HOP_FACTOR = [1.0, 1.0, 0.9, 0.55, 0.30, 0.15]   # hop 0..5 (hop 1 = direct counterparty)
BONUS = {"coinjoin": 0.25, "peel_chain": 0.15, "pass_through": 0.10}
TAINT_FACTOR = 0.9


@dataclass
class RiskResult:
    address: str
    score: int
    level: str
    factors: List[dict] = field(default_factory=list)
    exposure: Dict[str, dict] = field(default_factory=dict)

    def to_dict(self):
        return {"address": self.address, "score": self.score, "level": self.level,
                "factors": self.factors, "exposure": self.exposure}


def level_for(score: int) -> str:
    return "low" if score < 20 else "medium" if score < 50 else "high" if score < 75 else "severe"


def score_address(graph: TxGraph, db: LabelDB, target: str, heur: HeuristicResults,
                  taint: Dict[str, float], max_hops: int = 5) -> RiskResult:
    dist = {target: 0}
    dq = deque([target])
    while dq:
        cur = dq.popleft()
        if dist[cur] >= max_hops:
            continue
        for nb in graph.neighbors(cur):
            if nb not in dist:
                dist[nb] = dist[cur] + 1
                dq.append(nb)

    factors: List[dict] = []
    exposure: Dict[str, dict] = {}
    for addr, hop in dist.items():
        p = db.primary(addr)
        if not p or p.weight <= 0:
            continue
        c = p.weight * p.confidence * HOP_FACTOR[min(hop, len(HOP_FACTOR) - 1)]
        e = exposure.get(p.category)
        if e is None or c > e["contribution"]:
            exposure[p.category] = {"contribution": round(c, 4), "hop": hop, "entity": p.name, "address": addr}
    for cat, e in exposure.items():
        factors.append({"factor": f"{CATEGORIES[cat]['title']} exposure",
                        "detail": f"{e['entity']} ({'target' if e['hop'] == 0 else str(e['hop']) + ' hop(s)'})",
                        "contribution": e["contribution"]})

    t = taint.get(target, 0.0)
    if t > 0:
        factors.append({"factor": "Taint", "detail": f"{t:.1%} of received value traces to illicit sources",
                        "contribution": round(TAINT_FACTOR * t, 4)})

    near = {a for a, h in dist.items() if h <= 2}
    def touches(txids):
        for tid in txids:
            tx = graph.txs.get(tid)
            if tx and (near & (set(tx.input_addrs) | set(tx.output_addrs))):
                return True
        return False
    if any(touches([t]) for t in heur.coinjoins):
        factors.append({"factor": "Mixing", "detail": "CoinJoin within 2 hops", "contribution": BONUS["coinjoin"]})
    if any(touches(pc.txids) for pc in heur.peel_chains):
        factors.append({"factor": "Layering", "detail": "peel chain within 2 hops", "contribution": BONUS["peel_chain"]})
    if any(a in near and "pass-through" in graph.nodes[a].tags for a in graph.nodes):
        factors.append({"factor": "Layering", "detail": "rapid pass-through within 2 hops", "contribution": BONUS["pass_through"]})

    keep = 1.0
    for f in factors:
        keep *= 1 - min(0.99, f["contribution"])
    score = round(100 * (1 - keep))
    factors.sort(key=lambda f: -f["contribution"])
    return RiskResult(target, score, level_for(score), factors, exposure)
