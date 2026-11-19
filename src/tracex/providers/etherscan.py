"""Ethereum (and EVM chains) via the Etherscan v2 API. Requires ETHERSCAN_API_KEY in the environment."""
from __future__ import annotations

import os
from typing import List, Optional, Tuple

from ..models import Leg, Tx
from .base import Provider
from .http import HttpClient, ProviderError


class EtherscanProvider(Provider):
    name = "etherscan"
    chain = "eth"

    def __init__(self, chain_id: int = 1, proxy: Optional[str] = None, cache: bool = True, **_) -> None:
        self.key = os.environ.get("ETHERSCAN_API_KEY", "")
        if not self.key:
            raise ProviderError("ETHERSCAN_API_KEY environment variable is not set")
        self.chain_id = chain_id
        self.http = HttpClient("https://api.etherscan.io", rate_per_sec=4.0, cache=cache, proxy=proxy)

    def _call(self, **params):
        j = self.http.get_json("/v2/api", params={"chainid": self.chain_id, **params},
                               secret_params={"apikey": self.key}, ttl=900)
        if str(j.get("status")) == "0":
            res = j.get("result")
            if isinstance(res, list) or "No transactions" in str(j.get("message", "")):
                return []
            raise ProviderError(f"Etherscan: {j.get('message')} {str(res)[:80]}")
        return j.get("result", [])

    @staticmethod
    def _mk(r: dict, txid: str) -> Optional[Tx]:
        if r.get("isError") == "1":
            return None
        value = int(r.get("value", 0))
        frm = (r.get("from") or "").lower()
        to = (r.get("to") or r.get("contractAddress") or "").lower()
        if value == 0 or not frm or not to:
            return None
        fee = int(r.get("gasUsed", 0) or 0) * int(r.get("gasPrice", 0) or 0)
        return Tx(txid, "eth", int(r["timeStamp"]), int(r["blockNumber"]),
                  [Leg(frm, value)], [Leg(to, value)], fee)

    def get_address_txs(self, address: str, limit: int = 200) -> Tuple[List[Tx], bool]:
        base = dict(module="account", address=address, startblock=0, endblock=99999999,
                    page=1, offset=min(limit, 10000), sort="desc")
        txs: List[Tx] = []
        for r in self._call(action="txlist", **base):
            t = self._mk(r, r["hash"])
            if t:
                txs.append(t)
        for r in self._call(action="txlistinternal", **base):
            t = self._mk(r, f"{r['hash']}:{r.get('traceId', '0')}")
            if t:
                txs.append(t)
        txs.sort(key=lambda t: t.sort_key(), reverse=True)
        return txs[:limit], len(txs) >= limit

    def get_tx(self, txid: str) -> Tx:
        j = self.http.get_json("/v2/api", params={"chainid": self.chain_id, "module": "proxy",
                                                  "action": "eth_getTransactionByHash", "txhash": txid},
                               secret_params={"apikey": self.key}, ttl=86400)
        r = j.get("result") or {}
        if not r:
            raise ProviderError("transaction not found")
        value = int(r.get("value", "0x0"), 16)
        return Tx(txid, "eth", None, int(r["blockNumber"], 16) if r.get("blockNumber") else None,
                  [Leg(r["from"].lower(), value)], [Leg((r.get("to") or "").lower(), value)])
