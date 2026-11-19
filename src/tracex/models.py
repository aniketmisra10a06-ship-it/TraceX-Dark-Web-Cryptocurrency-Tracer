"""Chain-agnostic transaction model.

Both UTXO chains (Bitcoin family) and account chains (Ethereum family) are normalised
into the same shape: a transaction has *input legs* (who paid) and *output legs*
(who received). For account chains there is exactly one of each.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

DECIMALS = {"btc": 8, "ltc": 8, "bch": 8, "doge": 8, "eth": 18}
SYMBOL = {"btc": "BTC", "ltc": "LTC", "bch": "BCH", "doge": "DOGE", "eth": "ETH"}
UTXO_CHAINS = {"btc", "ltc", "bch", "doge"}


def to_coin(value: float, chain: str) -> float:
    """Convert base units (satoshi / wei) to whole coins."""
    return value / (10 ** DECIMALS.get(chain, 8))


@dataclass(frozen=True)
class Leg:
    address: str
    value: int  # base units


@dataclass
class Tx:
    txid: str
    chain: str
    timestamp: Optional[int]
    block_height: Optional[int]
    inputs: List[Leg]
    outputs: List[Leg]
    fee: int = 0
    coinbase: bool = False
    meta: Dict[str, Any] = field(default_factory=dict)

    @property
    def total_in(self) -> int:
        return sum(l.value for l in self.inputs)

    @property
    def total_out(self) -> int:
        return sum(l.value for l in self.outputs)

    @property
    def input_addrs(self) -> List[str]:
        return list(dict.fromkeys(l.address for l in self.inputs))

    @property
    def output_addrs(self) -> List[str]:
        return list(dict.fromkeys(l.address for l in self.outputs))

    @property
    def is_utxo(self) -> bool:
        return self.chain in UTXO_CHAINS

    def sort_key(self):
        return (self.timestamp or 0, self.block_height or 0, self.txid)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "txid": self.txid,
            "chain": self.chain,
            "timestamp": self.timestamp,
            "block_height": self.block_height,
            "inputs": [{"address": l.address, "value": l.value} for l in self.inputs],
            "outputs": [{"address": l.address, "value": l.value} for l in self.outputs],
            "fee": self.fee,
            "coinbase": self.coinbase,
        }

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "Tx":
        return Tx(
            txid=d["txid"],
            chain=d["chain"],
            timestamp=d.get("timestamp"),
            block_height=d.get("block_height"),
            inputs=[Leg(x["address"], int(x["value"])) for x in d["inputs"]],
            outputs=[Leg(x["address"], int(x["value"])) for x in d["outputs"]],
            fee=int(d.get("fee", 0)),
            coinbase=bool(d.get("coinbase", False)),
        )
