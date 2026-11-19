"""Taint (illicit-fund) propagation across the transaction graph.

haircut : output taint = value-weighted average of input taints (proportional, "fair" attribution)
poison  : any taint in the inputs fully taints every output (worst-case / compliance-strict view)
"""
from __future__ import annotations

from collections import defaultdict
from typing import Dict

from .graph import TxGraph


def propagate_taint(graph: TxGraph, sources: Dict[str, float], mode: str = "haircut") -> Dict[str, float]:
    if mode not in ("haircut", "poison"):
        raise ValueError("mode must be 'haircut' or 'poison'")
    taint: Dict[str, float] = dict(sources)
    recv_total: Dict[str, float] = defaultdict(float)
    recv_tainted: Dict[str, float] = defaultdict(float)
    for tx in graph.txs_sorted():
        if tx.coinbase:
            continue
        tin = tx.total_in
        if tin <= 0:
            continue
        t = sum(l.value * taint.get(l.address, 0.0) for l in tx.inputs) / tin
        if mode == "poison":
            t = 1.0 if t > 0 else 0.0
        for o in tx.outputs:
            recv_total[o.address] += o.value
            recv_tainted[o.address] += o.value * t
            if o.address not in sources and recv_total[o.address] > 0:
                taint[o.address] = recv_tainted[o.address] / recv_total[o.address]
    return {a: round(v, 6) for a, v in taint.items() if v > 0}
