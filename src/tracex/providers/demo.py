"""Offline synthetic scenario so you can try TraceX without network access or API keys.

EVERYTHING here is fictional: addresses are deliberately invalid (they contain underscores),
entity names are made up, and no real person, service, or wallet is represented.

Scenario ("Operation DemoLocker"):
  4 victims pay a ransom -> consolidation -> 4-step peel chain (cash-outs to an exchange,
  a darknet market, a casino) -> CoinJoin round -> no-KYC exchange. The market also forwards
  funds to a sanctioned (synthetic) entity.
"""
from __future__ import annotations

import hashlib
from collections import defaultdict
from typing import Dict, List, Tuple

from ..labels import Label
from ..models import Leg, Tx
from .base import Provider

B = 10 ** 8
T0 = 1767225600  # 2026-01-01 00:00:00 UTC
SEED_ADDRESS = "bc1q_demo_ransom_1"


def a(name: str) -> str:
    return f"bc1q_demo_{name}"


def demo_labels() -> List[Label]:
    src = "TraceX synthetic demo"
    return [
        Label(a("ransom_1"), "DemoLocker ransom wallet #1", "ransomware", src),
        Label(a("ransom_2"), "DemoLocker ransom wallet #2", "ransomware", src),
        Label(a("exch_kyc"), "DemoExchange deposit", "exchange_kyc", src),
        Label(a("exch_nokyc"), "ShadyEx (no-KYC)", "exchange_nokyc", src, 0.8),
        Label(a("market_1"), "DemoMarket escrow", "darknet_market", src),
        Label(a("market_hot"), "DemoMarket hot wallet", "darknet_market", src, 0.9),
        Label(a("casino"), "DemoCasino", "gambling", src),
        Label(a("sanctioned"), "Synthetic sanctioned entity", "sanctioned", src),
        Label(a("victim_1"), "Victim A", "victim", src),
        Label(a("victim_2"), "Victim B", "victim", src),
        Label(a("victim_3"), "Victim C", "victim", src),
        Label(a("victim_4"), "Victim D", "victim", src),
    ]


def _build() -> List[Tx]:
    txs: List[Tx] = []

    def T(hours: float, ins: List[Tuple[str, float]], outs: List[Tuple[str, float]], height_base=900000):
        li = [Leg(a(n), round(v * B)) for n, v in ins]
        lo = [Leg(a(n), round(v * B)) for n, v in outs]
        fee = sum(l.value for l in li) - sum(l.value for l in lo)
        assert fee >= 0, f"negative fee in demo tx {ins} -> {outs}"
        ts = T0 + int(hours * 3600)
        raw = f"{ts}{[(l.address, l.value) for l in li]}{[(l.address, l.value) for l in lo]}"
        txs.append(Tx(hashlib.sha256(raw.encode()).hexdigest(), "btc", ts, height_base + int(hours * 6), li, lo, fee))

    # 1) victims pay ransom (each keeps change)
    T(0,  [("victim_1", 1.0)], [("ransom_1", 0.50), ("victim_1c", 0.4995)])
    T(5,  [("victim_2", 1.5)], [("ransom_1", 0.80), ("victim_2c", 0.6995)])
    T(9,  [("victim_3", 2.0)], [("ransom_1", 1.20), ("victim_3c", 0.7995)])
    T(12, [("victim_4", 0.6)], [("ransom_2", 0.50), ("victim_4c", 0.0995)])
    # 2) operator consolidates two wallets in ONE tx (common-input-ownership => same entity)
    T(30, [("ransom_1", 2.5), ("ransom_2", 0.5)], [("collect", 2.999)])
    # 3) peel chain
    T(40, [("collect", 2.999)], [("peel_1", 0.20), ("chg_1", 2.7985)])
    T(52, [("chg_1", 2.7985)], [("peel_2", 0.25), ("chg_2", 2.5480)])
    T(70, [("chg_2", 2.5480)], [("peel_3", 0.30), ("chg_3", 2.2475)])
    T(90, [("chg_3", 2.2475)], [("peel_4", 0.21), ("chg_4", 2.0370)])
    # peels cash out
    T(41, [("peel_1", 0.20)], [("exch_kyc", 0.1995)])
    T(54, [("peel_2", 0.25)], [("market_1", 0.2495)])
    T(72, [("peel_3", 0.30)], [("casino", 0.2995)])
    T(91, [("peel_4", 0.21)], [("exch_kyc", 0.2095)])
    # 4) market side: other buyers pay the escrow; market consolidates and pays a sanctioned entity
    T(60, [("buyer_1", 0.1)], [("market_1", 0.0995)])
    T(65, [("buyer_2", 0.1)], [("market_1", 0.0995)])
    T(75, [("buyer_3", 0.1)], [("market_1", 0.0995)])
    T(100, [("market_1", 0.548)], [("market_hot", 0.5475)])
    T(110, [("market_hot", 0.5475)], [("sanctioned", 0.30), ("market_hot_c", 0.2465)])
    # 5) CoinJoin: operator's change + 4 other users, equal 2.0 outputs
    T(120, [("chg_4", 2.0370), ("user_1", 2.0), ("user_2", 2.0), ("user_3", 2.0), ("user_4", 2.0)],
        [("cj_out_1", 2.0), ("cj_out_2", 2.0), ("cj_out_3", 2.0), ("cj_out_4", 2.0), ("cj_out_5", 2.0),
         ("cj_chg", 0.0365)])
    # 6) post-mix cash-out to a no-KYC exchange, then a pass-through hop
    T(130, [("cj_out_1", 2.0)], [("hop_1", 1.9995)])
    T(130.2, [("hop_1", 1.9995)], [("exch_nokyc", 1.9990)])
    return txs


class DemoProvider(Provider):
    name = "demo"
    chain = "btc"

    def __init__(self) -> None:
        self._txs = _build()
        self._by_addr: Dict[str, List[Tx]] = defaultdict(list)
        self._by_id = {t.txid: t for t in self._txs}
        for t in self._txs:
            for addr in set(t.input_addrs) | set(t.output_addrs):
                self._by_addr[addr].append(t)

    def get_address_txs(self, address: str, limit: int = 200):
        txs = sorted(self._by_addr.get(address, []), key=lambda t: t.sort_key())
        return txs[:limit], len(txs) > limit

    def get_tx(self, txid: str) -> Tx:
        return self._by_id[txid]

    def address_tx_count(self, address: str):
        return len(self._by_addr.get(address, []))
