from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from typing import Optional

_HEX64 = re.compile(r"^[0-9a-fA-F]{64}$")
_ETH_TX = re.compile(r"^0x[0-9a-fA-F]{64}$")
_CTRL = re.compile(r"[\x00-\x1f\x7f]")


def short(addr: str, n: int = 20) -> str:
    if len(addr) <= n:
        return addr
    return f"{addr[:8]}…{addr[-6:]}"


def iso(ts: Optional[int]) -> str:
    if ts is None:
        return ""
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def utcnow_iso() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def is_txid(chain: str, s: str) -> bool:
    if chain == "eth":
        return bool(_ETH_TX.match(s))
    return bool(_HEX64.match(s))


def normalize_address(addr: str) -> str:
    addr = addr.strip()
    if addr.lower().startswith("0x"):
        return addr.lower()
    return addr


def clean_text(s: str, limit: int = 120) -> str:
    """Strip control characters and cap length. Used on every externally supplied string."""
    return _CTRL.sub("", str(s)).strip()[:limit]


def sha256_file(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def addr_type(addr: str) -> str:
    if addr.startswith(("bc1q", "ltc1q", "tb1q")):
        return "p2wpkh"
    if addr.startswith(("bc1p", "tb1p")):
        return "p2tr"
    if addr.startswith("3"):
        return "p2sh"
    if addr.startswith(("1", "L", "M")):
        return "p2pkh"
    if addr.startswith("0x"):
        return "eth"
    return "unknown"
