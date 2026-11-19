from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional, Tuple

from ..models import Tx


class Provider(ABC):
    """Read-only source of public ledger data."""

    name = "base"
    chain = "btc"

    @abstractmethod
    def get_address_txs(self, address: str, limit: int = 200) -> Tuple[List[Tx], bool]:
        """Return (transactions, truncated). `truncated` is True if more existed than `limit`."""

    @abstractmethod
    def get_tx(self, txid: str) -> Tx:
        ...

    def address_tx_count(self, address: str) -> Optional[int]:
        """Cheap lifetime tx count if the backend can provide it (used to skip hubs)."""
        return None
