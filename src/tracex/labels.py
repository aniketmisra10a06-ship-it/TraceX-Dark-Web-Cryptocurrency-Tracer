"""Entity label database.

TraceX ships **no** real-world address attributions. You bring your own labels
(OFAC SDN crypto addresses, vendor exports, your own case notes) as CSV or JSON.
"""
from __future__ import annotations

import csv
import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from .utils import clean_text, normalize_address

# weight = baseline AML risk of being exposed to this kind of entity (0..1)
CATEGORIES: Dict[str, Dict] = {
    "sanctioned":     {"weight": 1.00, "color": "#b91c1c", "title": "Sanctioned entity"},
    "ransomware":     {"weight": 0.95, "color": "#dc2626", "title": "Ransomware"},
    "theft":          {"weight": 0.90, "color": "#ea580c", "title": "Hack / theft proceeds"},
    "darknet_market": {"weight": 0.85, "color": "#9333ea", "title": "Darknet market"},
    "scam":           {"weight": 0.80, "color": "#c026d3", "title": "Fraud / scam"},
    "mixer":          {"weight": 0.60, "color": "#f59e0b", "title": "Mixer / tumbler"},
    "exchange_nokyc": {"weight": 0.40, "color": "#ca8a04", "title": "Exchange (no/weak KYC)"},
    "gambling":       {"weight": 0.30, "color": "#0284c7", "title": "Gambling"},
    "defi":           {"weight": 0.10, "color": "#0d9488", "title": "DeFi protocol"},
    "exchange_kyc":   {"weight": 0.05, "color": "#16a34a", "title": "Exchange (KYC)"},
    "service":        {"weight": 0.05, "color": "#64748b", "title": "Other service"},
    "victim":         {"weight": 0.00, "color": "#2563eb", "title": "Victim"},
    "unlabeled":      {"weight": 0.00, "color": "#94a3b8", "title": "Unlabeled"},
}


@dataclass
class Label:
    address: str
    name: str
    category: str
    source: str = ""
    confidence: float = 1.0
    notes: str = ""

    @property
    def weight(self) -> float:
        return CATEGORIES.get(self.category, CATEGORIES["unlabeled"])["weight"]

    def to_dict(self):
        return asdict(self)


class LabelDB:
    def __init__(self) -> None:
        self._by_addr: Dict[str, List[Label]] = {}
        self.warnings: List[str] = []
        self.sources: List[str] = []

    def __len__(self) -> int:
        return sum(len(v) for v in self._by_addr.values())

    def add(self, label: Label) -> None:
        self._by_addr.setdefault(label.address, []).append(label)

    def get(self, address: str) -> List[Label]:
        return self._by_addr.get(normalize_address(address), [])

    def primary(self, address: str) -> Optional[Label]:
        ls = self.get(address)
        if not ls:
            return None
        return max(ls, key=lambda l: (l.weight * l.confidence, l.confidence))

    def category(self, address: str) -> str:
        p = self.primary(address)
        return p.category if p else "unlabeled"

    def addresses(self) -> Iterable[str]:
        return self._by_addr.keys()

    # ---------------------------------------------------------------- loading
    def _ingest(self, rows: Iterable[dict], origin: str) -> None:
        for i, r in enumerate(rows, 1):
            addr = normalize_address(str(r.get("address", "")))
            if not addr or len(addr) > 128:
                self.warnings.append(f"{origin}:{i}: missing/invalid address, skipped")
                continue
            cat = clean_text(r.get("category", "unlabeled"), 40).lower()
            if cat not in CATEGORIES:
                self.warnings.append(f"{origin}:{i}: unknown category '{cat}' -> 'unlabeled'")
                cat = "unlabeled"
            try:
                conf = float(r.get("confidence", 1.0) or 1.0)
            except (TypeError, ValueError):
                conf = 1.0
            conf = max(0.0, min(1.0, conf))
            self.add(Label(addr, clean_text(r.get("name", "unnamed"), 120) or "unnamed", cat,
                           clean_text(r.get("source", ""), 120), conf, clean_text(r.get("notes", ""), 300)))

    def load(self, path: str) -> "LabelDB":
        p = Path(path)
        if p.suffix.lower() == ".json":
            data = json.loads(p.read_text(encoding="utf-8"))
            rows = data.get("labels", []) if isinstance(data, dict) else data
            self._ingest(rows, p.name)
        else:
            with p.open(newline="", encoding="utf-8-sig") as f:
                self._ingest(csv.DictReader(f), p.name)
        self.sources.append(str(p))
        return self


def load_labels(paths: Iterable[str], include_demo: bool = False) -> LabelDB:
    db = LabelDB()
    for p in paths:
        db.load(p)
    if include_demo:
        from .providers.demo import demo_labels
        for l in demo_labels():
            db.add(l)
        db.sources.append("builtin:demo")
    return db
