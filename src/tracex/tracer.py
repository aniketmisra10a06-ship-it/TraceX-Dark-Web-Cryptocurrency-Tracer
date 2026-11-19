"""Breadth-first fund-flow tracer."""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Set, Tuple

from .graph import TxGraph
from .labels import LabelDB
from .providers.base import Provider
from .utils import is_txid, normalize_address, short

# Endpoints we record but do not expand through (hot wallets have enormous fan-in/out).
DEFAULT_STOP = ("exchange_kyc", "exchange_nokyc", "defi", "service")


@dataclass
class TraceConfig:
    chain: str = "btc"
    depth: int = 3
    direction: str = "both"                  # forward | backward | both
    max_txs_per_address: int = 200
    max_nodes: int = 1500
    min_value: int = 0                       # base units; ignore edges below this (dust filter)
    hub_threshold: int = 1000                # lifetime tx count above which an address is a "hub"
    stop_categories: Tuple[str, ...] = DEFAULT_STOP
    since: Optional[int] = None
    until: Optional[int] = None

    def to_dict(self) -> Dict:
        d = dict(self.__dict__)
        d["stop_categories"] = list(self.stop_categories)
        return d


class Tracer:
    def __init__(self, provider: Provider, labels: LabelDB, cfg: TraceConfig,
                 progress: Optional[Callable[[str], None]] = None) -> None:
        self.p, self.db, self.cfg = provider, labels, cfg
        self.progress = progress or (lambda m: None)
        self.graph = TxGraph(cfg.chain)
        self._cache: Dict[str, Tuple[list, bool]] = {}
        self.skipped_hubs: List[str] = []
        self.truncated: List[str] = []

    def _fetch(self, addr: str):
        if addr not in self._cache:
            self._cache[addr] = self.p.get_address_txs(addr, self.cfg.max_txs_per_address)
        return self._cache[addr]

    def _in_window(self, ts: Optional[int]) -> bool:
        if ts is None:
            return True
        return (self.cfg.since is None or ts >= self.cfg.since) and (self.cfg.until is None or ts <= self.cfg.until)

    def resolve_seeds(self, seeds: List[str]) -> List[str]:
        out: List[str] = []
        for s in seeds:
            s = normalize_address(s)
            if is_txid(self.cfg.chain, s):
                tx = self.p.get_tx(s)
                self.graph.add_tx(tx)
                self.progress(f"seed transaction {short(s, 16)}: {len(tx.inputs)} in / {len(tx.outputs)} out")
                if self.cfg.direction in ("forward", "both"):
                    out += tx.output_addrs
                if self.cfg.direction in ("backward", "both"):
                    out += tx.input_addrs
            else:
                out.append(s)
        return list(dict.fromkeys(out))

    def trace(self, seeds: List[str]) -> TxGraph:
        cfg, g = self.cfg, self.graph
        seeds = self.resolve_seeds(seeds)
        dirs = ["forward", "backward"] if cfg.direction == "both" else [cfg.direction]
        dq: deque = deque()
        done: Set[Tuple[str, str]] = set()
        for s in seeds:
            n = g.node(s)
            n.is_seed, n.depth = True, 0
            for d in dirs:
                dq.append((s, 0, d))
        expanded = 0
        while dq:
            addr, depth, d = dq.popleft()
            if (addr, d) in done or depth >= cfg.depth:
                continue
            done.add((addr, d))
            node = g.node(addr)
            node.tags.add("fwd" if d == "forward" else "bwd")
            p = self.db.primary(addr)
            if not node.is_seed and p and p.category in cfg.stop_categories:
                node.tags.add("endpoint")
                continue
            cnt = self.p.address_tx_count(addr)
            if cnt is not None and cnt > cfg.hub_threshold and not node.is_seed:
                node.tags.add("hub")
                self.skipped_hubs.append(addr)
                continue
            txs, trunc = self._fetch(addr)
            if trunc:
                node.tags.add("truncated")
                if addr not in self.truncated:
                    self.truncated.append(addr)
            expanded += 1
            self.progress(f"[{expanded}] {d[:3]} depth={depth} {short(addr)} ({len(txs)} txs, {len(g.nodes)} nodes)")
            for tx in txs:
                if not self._in_window(tx.timestamp):
                    continue
                if d == "forward" and addr in tx.input_addrs:
                    nxt = [l.address for l in tx.outputs if l.value >= cfg.min_value and l.address != addr]
                    sign = 1
                elif d == "backward" and addr in tx.output_addrs:
                    nxt = [l.address for l in tx.inputs if l.value >= cfg.min_value and l.address != addr]
                    sign = -1
                else:
                    continue
                g.add_tx(tx)
                for nb in dict.fromkeys(nxt):
                    if len(g.nodes) >= cfg.max_nodes:
                        self.progress(f"node cap {cfg.max_nodes} reached - stopping expansion")
                        dq.clear()
                        break
                    n2 = g.node(nb)
                    nd = sign * (depth + 1)
                    if n2.depth is None or abs(nd) < abs(n2.depth):
                        n2.depth = nd
                    dq.append((nb, depth + 1, d))
        self._place_incidental(g)
        return g

    @staticmethod
    def _place_incidental(g: TxGraph) -> None:
        """Nodes that only appear as siblings inside a traced transaction (e.g. other CoinJoin
        participants, change outputs) were never expanded; give them a sensible hop column."""
        for _ in range(len(g.nodes)):
            changed = False
            for a, n in g.nodes.items():
                if n.depth is not None:
                    continue
                preds = [g.nodes[p].depth for p in g.pred.get(a, ()) if g.nodes[p].depth is not None]
                succs = [g.nodes[s].depth for s in g.succ.get(a, ()) if g.nodes[s].depth is not None]
                if preds:
                    p = min(preds, key=abs)
                    n.depth = p + 1 if p >= 0 else p
                elif succs:
                    s = min(succs, key=abs)
                    n.depth = s - 1 if s > 0 else s
                else:
                    continue
                changed = True
            if not changed:
                break
        for n in g.nodes.values():
            if n.depth is None:
                n.depth = 0
