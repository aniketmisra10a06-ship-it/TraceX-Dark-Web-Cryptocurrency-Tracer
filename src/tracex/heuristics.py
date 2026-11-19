"""Forensic heuristics: clustering, CoinJoin, peel chains, change detection, behavioural patterns.

All heuristics are PROBABILISTIC. They produce investigative leads, not proof.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from .graph import TxGraph
from .labels import CATEGORIES, LabelDB
from .models import Tx, to_coin
from .utils import addr_type, short

SEVERITY_ORDER = {"info": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}


@dataclass
class Finding:
    kind: str
    severity: str
    title: str
    detail: str
    txids: List[str] = field(default_factory=list)
    addresses: List[str] = field(default_factory=list)

    def to_dict(self):
        return {"kind": self.kind, "severity": self.severity, "title": self.title, "detail": self.detail,
                "txids": self.txids[:50], "addresses": self.addresses[:50]}


@dataclass
class Cluster:
    id: int
    members: List[str]
    name: str = ""
    category: str = "unlabeled"
    evidence_txids: List[str] = field(default_factory=list)


@dataclass
class PeelChain:
    txids: List[str]
    peel_addresses: List[str]
    change_addresses: List[str]
    total_peeled: float


@dataclass
class HeuristicResults:
    findings: List[Finding] = field(default_factory=list)
    clusters: List[Cluster] = field(default_factory=list)
    coinjoins: Dict[str, dict] = field(default_factory=dict)
    peel_chains: List[PeelChain] = field(default_factory=list)
    change: Dict[str, Tuple[str, float, List[str]]] = field(default_factory=dict)


# ------------------------------------------------------------------ CoinJoin
def detect_coinjoin(tx: Tx) -> Optional[dict]:
    """Equal-output-value CoinJoin signature (Whirlpool / Wasabi / JoinMarket style)."""
    if not tx.is_utxo or len(tx.inputs) < 3 or len(tx.outputs) < 3:
        return None
    counts = Counter(l.value for l in tx.outputs)
    value, k = counts.most_common(1)[0]
    if k >= 3 and k >= 0.5 * len(tx.outputs) and len(tx.input_addrs) >= 3:
        return {"equal_value": value, "participants": k, "inputs": len(tx.inputs), "outputs": len(tx.outputs)}
    return None


# ------------------------------------------------------------- clustering
class _UF:
    def __init__(self) -> None:
        self.p: Dict[str, str] = {}

    def find(self, x: str) -> str:
        self.p.setdefault(x, x)
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def union(self, a: str, b: str) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[ra] = rb


def cluster_common_input(graph: TxGraph, coinjoins: Dict[str, dict], db: LabelDB) -> List[Cluster]:
    """Common-input-ownership heuristic (CIOH). CoinJoins are excluded: their inputs belong to
    different parties, so merging them would create false mega-clusters."""
    uf = _UF()
    evidence: Dict[str, List[str]] = defaultdict(list)
    for tx in graph.txs.values():
        if not tx.is_utxo or tx.txid in coinjoins:
            continue
        ins = tx.input_addrs
        if len(ins) >= 2:
            for x in ins[1:]:
                uf.union(ins[0], x)
            evidence[ins[0]].append(tx.txid)
    groups: Dict[str, Set[str]] = defaultdict(set)
    for a in list(uf.p):
        groups[uf.find(a)].add(a)
    out: List[Cluster] = []
    for members in sorted((g for g in groups.values() if len(g) >= 2), key=lambda g: (-len(g), sorted(g)[0])):
        ml = sorted(members)
        c = Cluster(id=len(out) + 1, members=ml)
        best = None
        for m in ml:
            p = db.primary(m)
            if p and (best is None or p.weight > best.weight):
                best = p
        if best:
            c.name, c.category = best.name, best.category
        c.evidence_txids = [t for m in ml for t in evidence.get(m, [])][:20]
        out.append(c)
    return out


# ------------------------------------------------------------ change addr
def likely_change(tx: Tx, first_seen_tx: Dict[str, str]) -> Optional[Tuple[str, float, List[str]]]:
    """Return (change_address, confidence, reasons) for 2-output UTXO transactions."""
    if not tx.is_utxo or len(tx.outputs) != 2 or tx.coinbase:
        return None
    o1, o2 = tx.outputs
    if o1.address == o2.address:
        return None
    votes = {o1.address: [], o2.address: []}
    new1 = first_seen_tx.get(o1.address) == tx.txid
    new2 = first_seen_tx.get(o2.address) == tx.txid
    if new1 and not new2:
        votes[o1.address].append("fresh address (first seen in this tx)")
    if new2 and not new1:
        votes[o2.address].append("fresh address (first seen in this tx)")
    step = 10 ** 5  # 0.001 BTC
    r1, r2 = o1.value % step == 0, o2.value % step == 0
    if r1 and not r2:
        votes[o2.address].append("other output is a round amount (payment)")
    if r2 and not r1:
        votes[o1.address].append("other output is a round amount (payment)")
    in_types = {addr_type(a) for a in tx.input_addrs}
    t1, t2 = addr_type(o1.address) in in_types, addr_type(o2.address) in in_types
    if t1 and not t2:
        votes[o1.address].append("same script type as inputs")
    if t2 and not t1:
        votes[o2.address].append("same script type as inputs")
    a, b = o1.address, o2.address
    if len(votes[a]) == len(votes[b]):
        return None
    best = a if len(votes[a]) > len(votes[b]) else b
    return best, min(1.0, len(votes[best]) / 3), votes[best]


# -------------------------------------------------------------- peel chain
def detect_peel_chains(graph: TxGraph, change_map, min_len: int = 3) -> List[PeelChain]:
    txs = graph.txs_sorted()
    spends: Dict[str, List[Tx]] = defaultdict(list)
    for t in txs:
        for a in t.input_addrs:
            spends[a].append(t)

    def step(t: Tx):
        if not t.is_utxo or len(t.input_addrs) > 2 or len(t.outputs) != 2:
            return None
        big, small = sorted(t.outputs, key=lambda l: -l.value)
        if big.address == small.address or small.value > 0.5 * big.value or small.value == 0:
            return None
        ch = change_map.get(t.txid)
        if ch and ch[0] == small.address and ch[1] >= 0.66:
            return None  # heuristics say the small output is the change
        return big.address, small.address

    steps = {t.txid: step(t) for t in txs}
    is_successor: Set[str] = set()
    nxt: Dict[str, Optional[Tx]] = {}
    for t in txs:
        s = steps[t.txid]
        nxt[t.txid] = None
        if not s:
            continue
        for cand in spends.get(s[0], []):
            if cand.sort_key() > t.sort_key() and steps.get(cand.txid):
                nxt[t.txid] = cand
                is_successor.add(cand.txid)
                break
    chains: List[PeelChain] = []
    for t in txs:
        if not steps[t.txid] or t.txid in is_successor:
            continue
        seq, seen, cur = [], set(), t
        while cur and cur.txid not in seen:
            seq.append(cur)
            seen.add(cur.txid)
            cur = nxt.get(cur.txid)
        if len(seq) >= min_len:
            peels = [steps[x.txid][1] for x in seq]
            chg = [steps[x.txid][0] for x in seq]
            small_total = 0.0
            for x in seq:
                small_total += to_coin(min(l.value for l in x.outputs), x.chain)
            chains.append(PeelChain([x.txid for x in seq], peels, chg, small_total))
    return chains


# ------------------------------------------------------------ orchestrator
def run_heuristics(graph: TxGraph, db: LabelDB, passthrough_minutes: int = 60) -> HeuristicResults:
    res = HeuristicResults()
    txs = graph.txs_sorted()
    chain = graph.chain

    first_seen: Dict[str, str] = {}
    for t in txs:
        for a in t.input_addrs + t.output_addrs:
            first_seen.setdefault(a, t.txid)

    for t in txs:
        cj = detect_coinjoin(t)
        if cj:
            res.coinjoins[t.txid] = cj
            res.findings.append(Finding(
                "coinjoin", "medium", "CoinJoin / mixing transaction",
                f"{cj['participants']} equal outputs of {to_coin(cj['equal_value'], chain):g} {chain.upper()} "
                f"({cj['inputs']} inputs -> {cj['outputs']} outputs). Output links to inputs are deliberately "
                f"ambiguous; downstream attribution confidence is reduced.",
                [t.txid], [l.address for l in t.outputs]))
        ch = likely_change(t, first_seen)
        if ch:
            res.change[t.txid] = ch

    res.clusters = cluster_common_input(graph, res.coinjoins, db)
    for c in res.clusters:
        for m in c.members:
            graph.node(m).cluster = c.id
        res.findings.append(Finding(
            "cluster", "info", f"Address cluster #{c.id} ({len(c.members)} addresses)",
            "Addresses spent together as inputs of one transaction (common-input-ownership)."
            + (f" Cluster inherits label: {c.name} [{c.category}]." if c.name else ""),
            c.evidence_txids, c.members))

    res.peel_chains = detect_peel_chains(graph, res.change)
    for pc in res.peel_chains:
        ends = [a for a in pc.peel_addresses if db.get(a)]
        names = ", ".join(sorted({db.primary(a).name for a in ends})) if ends else "no labeled endpoints"
        res.findings.append(Finding(
            "peel_chain", "medium", f"Peel chain of {len(pc.txids)} hops",
            f"Large balance repeatedly split into a small 'peel' payment and a large change output; "
            f"{pc.total_peeled:g} {chain.upper()} peeled in total. Peel endpoints: {names}.",
            pc.txids, pc.peel_addresses + pc.change_addresses))

    for t in txs:
        if t.is_utxo and not t.coinbase and len(t.inputs) >= 10 and len(t.outputs) <= 2 and t.txid not in res.coinjoins:
            res.findings.append(Finding("consolidation", "low", f"Consolidation: {len(t.inputs)} inputs -> {len(t.outputs)}",
                                        "Many UTXOs swept into few outputs (wallet consolidation / collection).",
                                        [t.txid], t.output_addrs))
        if len(t.outputs) >= 10 and len(t.input_addrs) <= 2 and t.txid not in res.coinjoins:
            res.findings.append(Finding("fan_out", "low", f"Fan-out: {len(t.input_addrs)} -> {len(t.outputs)} outputs",
                                        "One source distributing to many recipients (payout / splitting).",
                                        [t.txid], t.output_addrs[:50]))

    # rapid pass-through: address receives and forwards >=90% of what it got within N minutes
    recv: Dict[str, List[Tuple[int, int]]] = defaultdict(list)
    sent: Dict[str, List[Tuple[int, int]]] = defaultdict(list)
    for t in txs:
        if t.timestamp is None:
            continue
        for l in t.outputs:
            recv[l.address].append((t.timestamp, l.value))
        for l in t.inputs:
            sent[l.address].append((t.timestamp, l.value))
    pt = []
    for a, r in recv.items():
        if a not in sent or db.get(a) and db.primary(a).category in ("exchange_kyc", "exchange_nokyc", "service", "defi"):
            continue
        r_total, s_total = sum(v for _, v in r), sum(v for _, v in sent[a])
        gap = min(ts for ts, _ in sent[a]) - min(ts for ts, _ in r)
        if r_total and s_total >= 0.9 * r_total and 0 <= gap <= passthrough_minutes * 60 \
                and a in graph.pred and a in graph.succ:
            pt.append(a)
            graph.node(a).tags.add("pass-through")
    if pt:
        res.findings.append(Finding(
            "pass_through", "medium", f"{len(pt)} rapid pass-through address(es)",
            f"Addresses that forwarded >=90% of received funds within {passthrough_minutes} minutes - "
            f"typical of layering / relay wallets.", [], pt))

    # tags for report visuals
    for t in res.coinjoins:
        for l in graph.txs[t].outputs:
            graph.node(l.address).tags.add("coinjoin-output")
    for pc in res.peel_chains:
        for x in pc.change_addresses:
            graph.node(x).tags.add("peel-change")
        for x in pc.peel_addresses:
            graph.node(x).tags.add("peel-payment")

    # labeled exposures
    for addr, n in graph.nodes.items():
        p = db.primary(addr)
        if not p:
            continue
        n.labels = list(db.get(addr))
        if p.weight >= 0.5:
            sev = "critical" if p.weight >= 0.9 else "high"
            res.findings.append(Finding(
                "labeled_entity", sev, f"{CATEGORIES[p.category]['title']}: {p.name}",
                f"Address {short(addr)} is labeled '{p.name}' ({p.category}, confidence {p.confidence:.0%}, "
                f"source: {p.source or 'n/a'}) and appears in the traced flow.", [], [addr]))
    res.findings.sort(key=lambda f: -SEVERITY_ORDER[f.severity])
    return res
