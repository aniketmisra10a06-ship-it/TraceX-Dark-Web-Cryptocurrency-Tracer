"""In-memory address graph built from transactions."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from .labels import Label
from .models import Tx

MAX_PAIRWISE = 2500   # cap on in*out edge expansion for a single huge transaction
TOP_SIDE = 50


@dataclass
class Node:
    address: str
    chain: str
    received: int = 0
    sent: int = 0
    tx_count: int = 0
    first_seen: Optional[int] = None
    last_seen: Optional[int] = None
    depth: Optional[int] = None      # signed hop distance from seed (+ forward, - backward)
    labels: List[Label] = field(default_factory=list)
    cluster: Optional[int] = None
    taint: float = 0.0
    is_seed: bool = False
    tags: Set[str] = field(default_factory=set)

    @property
    def volume(self) -> int:
        return self.received + self.sent


@dataclass
class Edge:
    src: str
    dst: str
    value: float = 0.0
    count: int = 0
    txids: List[str] = field(default_factory=list)
    first: Optional[int] = None
    last: Optional[int] = None


class TxGraph:
    def __init__(self, chain: str = "btc") -> None:
        self.chain = chain
        self.txs: Dict[str, Tx] = {}
        self.nodes: Dict[str, Node] = {}
        self.edges: Dict[Tuple[str, str], Edge] = {}
        self.succ: Dict[str, Set[str]] = defaultdict(set)
        self.pred: Dict[str, Set[str]] = defaultdict(set)

    def node(self, address: str) -> Node:
        n = self.nodes.get(address)
        if n is None:
            n = self.nodes[address] = Node(address, self.chain)
        return n

    def add_tx(self, tx: Tx) -> bool:
        if tx.txid in self.txs:
            return False
        self.txs[tx.txid] = tx
        ts = tx.timestamp
        touched = set(tx.input_addrs) | set(tx.output_addrs)
        for a in touched:
            n = self.node(a)
            n.tx_count += 1
            if ts is not None:
                n.first_seen = ts if n.first_seen is None else min(n.first_seen, ts)
                n.last_seen = ts if n.last_seen is None else max(n.last_seen, ts)
        for l in tx.inputs:
            self.node(l.address).sent += l.value
        for l in tx.outputs:
            self.node(l.address).received += l.value
        self._add_edges(tx)
        return True

    def _add_edges(self, tx: Tx) -> None:
        if tx.coinbase or not tx.inputs or not tx.outputs:
            return
        total_in = tx.total_in
        if total_in <= 0:
            return
        ins, outs = tx.inputs, tx.outputs
        if len(ins) * len(outs) > MAX_PAIRWISE:
            ins = sorted(ins, key=lambda l: -l.value)[:TOP_SIDE]
            outs = sorted(outs, key=lambda l: -l.value)[:TOP_SIDE]
            total_in = sum(l.value for l in ins)
        seen: Set[Tuple[str, str]] = set()
        for i in ins:
            for o in outs:
                if i.address == o.address:
                    continue                      # change returned to self
                key = (i.address, o.address)
                share = i.value * o.value / total_in   # proportional attribution
                e = self.edges.get(key)
                if e is None:
                    e = self.edges[key] = Edge(i.address, o.address)
                e.value += share
                if key not in seen:
                    e.count += 1
                    e.txids.append(tx.txid)
                    seen.add(key)
                if tx.timestamp is not None:
                    e.first = tx.timestamp if e.first is None else min(e.first, tx.timestamp)
                    e.last = tx.timestamp if e.last is None else max(e.last, tx.timestamp)
                self.succ[i.address].add(o.address)
                self.pred[o.address].add(i.address)

    def neighbors(self, address: str) -> Set[str]:
        return self.succ.get(address, set()) | self.pred.get(address, set())

    def txs_sorted(self) -> List[Tx]:
        return sorted(self.txs.values(), key=lambda t: t.sort_key())
