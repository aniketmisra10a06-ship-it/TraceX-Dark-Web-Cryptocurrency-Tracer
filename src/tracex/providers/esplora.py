"""Bitcoin via any Esplora-compatible API (blockstream.info, mempool.space, self-hosted)."""
from __future__ import annotations

from typing import List, Optional, Tuple

from ..models import Leg, Tx
from .base import Provider
from .http import HttpClient


class EsploraProvider(Provider):
    name = "esplora"
    chain = "btc"

    def __init__(self, base_url: str = "https://blockstream.info/api", proxy: Optional[str] = None,
                 cache: bool = True, rate_per_sec: float = 3.0, **_) -> None:
        self.http = HttpClient(base_url, rate_per_sec=rate_per_sec, cache=cache, proxy=proxy)

    @staticmethod
    def _parse(j: dict) -> Tx:
        ins, coinbase = [], False
        for v in j.get("vin", []):
            if v.get("is_coinbase"):
                coinbase = True
                continue
            po = v.get("prevout") or {}
            addr = po.get("scriptpubkey_address")
            if addr:
                ins.append(Leg(addr, int(po.get("value", 0))))
        outs = [Leg(o["scriptpubkey_address"], int(o.get("value", 0)))
                for o in j.get("vout", []) if o.get("scriptpubkey_address")]
        st = j.get("status", {})
        return Tx(j["txid"], "btc", st.get("block_time"), st.get("block_height"), ins, outs,
                  int(j.get("fee", 0)), coinbase)

    def address_tx_count(self, address: str) -> Optional[int]:
        j = self.http.get_json(f"/address/{address}", ttl=900)
        return j.get("chain_stats", {}).get("tx_count", 0) + j.get("mempool_stats", {}).get("tx_count", 0)

    def get_tx(self, txid: str) -> Tx:
        return self._parse(self.http.get_json(f"/tx/{txid}", ttl=86400))

    def get_address_txs(self, address: str, limit: int = 200) -> Tuple[List[Tx], bool]:
        out: List[Tx] = []
        page = self.http.get_json(f"/address/{address}/txs", ttl=900)
        while page:
            out.extend(self._parse(j) for j in page)
            confirmed = [j for j in page if j.get("status", {}).get("confirmed")]
            if len(out) >= limit or len(confirmed) < 25:
                break
            page = self.http.get_json(f"/address/{address}/txs/chain/{confirmed[-1]['txid']}", ttl=900)
        return out[:limit], len(out) > limit or (len(out) == limit)
