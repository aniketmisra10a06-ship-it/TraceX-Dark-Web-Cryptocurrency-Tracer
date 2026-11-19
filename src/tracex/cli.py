"""TraceX command-line interface."""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

from . import __version__
from .analysis import investigate
from .banner import print_banner
from .labels import CATEGORIES, load_labels
from .models import DECIMALS
from .providers import make_provider
from .providers.demo import SEED_ADDRESS
from .providers.http import ProviderError
from .reports import ALL_FORMATS, write_all
from .tracer import TraceConfig, Tracer


def _ts(s):
    if not s:
        return None
    return int(datetime.strptime(s, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp())


def _log(msg: str) -> None:
    print(msg, file=sys.stderr)


def _run(args, seeds, provider, labels) -> int:
    cfg = TraceConfig(
        chain=args.chain, depth=args.depth, direction=args.direction,
        max_txs_per_address=args.max_txs, max_nodes=args.max_nodes,
        min_value=int(args.min_value * 10 ** DECIMALS.get(args.chain, 8)),
        hub_threshold=args.hub_threshold, since=_ts(args.since), until=_ts(args.until),
    )
    _log(f"[*] provider={provider.name} chain={cfg.chain} depth={cfg.depth} direction={cfg.direction} "
         f"labels={len(labels)}")
    for w in labels.warnings[:5]:
        _log(f"[!] label warning: {w}")
    tr = Tracer(provider, labels, cfg, progress=(_log if args.verbose else None))
    try:
        g = tr.trace(seeds)
    except ProviderError as e:
        _log(f"[x] data provider error: {e}")
        return 2
    _log(f"[+] traced {len(g.nodes)} addresses / {len(g.txs)} transactions")
    if tr.skipped_hubs:
        _log(f"[!] skipped {len(tr.skipped_hubs)} hub address(es) (> {cfg.hub_threshold} txs)")
    if tr.truncated:
        _log(f"[!] {len(tr.truncated)} address(es) had more than {cfg.max_txs_per_address} txs (history truncated)")
    if not g.txs:
        _log("[x] no transactions found for the given seed(s)")
        return 1
    inv = investigate(g, labels, [s for s in seeds if s in g.nodes] or list(g.nodes)[:1],
                      meta={"provider": provider.name, "seeds_input": seeds, "config": cfg.to_dict(),
                            "label_sources": labels.sources},
                      taint_mode=args.taint_mode, taint_sources=args.taint_source)
    files = write_all(inv, args.out, args.formats)
    for r in inv.risk.values():
        _log(f"[=] risk {r.address[:28]}: {r.score}/100 ({r.level})")
    _log(f"[+] {len(inv.heur.findings)} findings · {len(inv.heur.clusters)} clusters · "
         f"{len(inv.heur.coinjoins)} coinjoins · {len(inv.heur.peel_chains)} peel chains")
    _log(f"[+] wrote {len(files)} files to {Path(args.out).resolve()}")
    html = Path(args.out) / "report.html"
    if html.exists():
        _log(f"[>] open: {html.resolve()}")
    return 0


def _nobanner(p: argparse.ArgumentParser) -> None:
    # SUPPRESS so a sub-command default never overwrites the top-level value
    p.add_argument("--no-banner", action="store_true", default=argparse.SUPPRESS, help="hide the start-up banner")


def _common(p: argparse.ArgumentParser) -> None:
    p.add_argument("--chain", default="btc", choices=sorted(DECIMALS), help="chain (default btc)")
    p.add_argument("-d", "--depth", type=int, default=3, help="max hops from each seed (default 3)")
    p.add_argument("--direction", default="both", choices=["forward", "backward", "both"])
    p.add_argument("--max-txs", type=int, default=200, help="max transactions pulled per address")
    p.add_argument("--max-nodes", type=int, default=1500, help="hard cap on graph size")
    p.add_argument("--min-value", type=float, default=0.0, help="dust filter in whole coins")
    p.add_argument("--hub-threshold", type=int, default=1000, help="skip addresses with more lifetime txs")
    p.add_argument("--since", help="YYYY-MM-DD, ignore older txs")
    p.add_argument("--until", help="YYYY-MM-DD, ignore newer txs")
    p.add_argument("--taint-mode", default="haircut", choices=["haircut", "poison"])
    p.add_argument("--taint-source", action="append", default=[], help="extra address to treat as 100%% tainted")
    p.add_argument("-l", "--labels", action="append", default=[], help="label CSV/JSON (repeatable)")
    p.add_argument("-o", "--out", default="tracex-report", help="output directory")
    p.add_argument("-f", "--formats", nargs="+", default=["all"], choices=["all"] + ALL_FORMATS)
    p.add_argument("-v", "--verbose", action="store_true")
    _nobanner(p)


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="tracex", description="TraceX - blockchain forensics & AML tracing (by Aniket Misra)")
    ap.add_argument("--version", action="version", version=f"TraceX {__version__}")
    ap.add_argument("--no-banner", action="store_true", help="hide the start-up banner")
    sub = ap.add_subparsers(dest="cmd")

    t = sub.add_parser("trace", help="trace addresses / transactions on a live chain")
    t.add_argument("seeds", nargs="+", help="address(es) or txid(s)")
    t.add_argument("--provider", default=None, choices=["esplora", "etherscan", "demo"])
    t.add_argument("--esplora-url", default="https://blockstream.info/api")
    t.add_argument("--proxy", help="HTTP(S) proxy URL for provider traffic (e.g. a Tor HTTP gateway)")
    t.add_argument("--no-cache", action="store_true")
    _common(t)

    d = sub.add_parser("demo", help="run the offline synthetic scenario (no network, no API key)")
    _common(d)
    d.set_defaults(out="tracex-demo", depth=8)

    lb = sub.add_parser("labels", help="validate a label file and print a summary")
    lb.add_argument("files", nargs="+")
    _nobanner(lb)
    _nobanner(sub.add_parser("categories", help="list entity categories and base risk weights"))
    return ap


def main(argv=None) -> int:
    ap = build_parser()
    args = ap.parse_args(argv)
    if not args.cmd:
        print_banner()
        ap.print_help()
        return 0
    if not getattr(args, "no_banner", False):
        print_banner()

    if args.cmd == "categories":
        for k, v in CATEGORIES.items():
            print(f"{k:16} weight={v['weight']:.2f}  {v['title']}")
        return 0
    if args.cmd == "labels":
        db = load_labels(args.files)
        print(f"{len(db)} labels loaded from {len(args.files)} file(s)")
        for w in db.warnings:
            print("warning:", w)
        return 1 if db.warnings else 0
    if args.cmd == "demo":
        labels = load_labels(args.labels, include_demo=True)
        return _run(args, [SEED_ADDRESS], make_provider("demo"), labels)
    if args.cmd == "trace":
        name = args.provider or ("etherscan" if args.chain == "eth" else "esplora")
        try:
            prov = make_provider(name, args.chain, base_url=args.esplora_url, proxy=args.proxy,
                                 cache=not args.no_cache) if name == "esplora" else \
                make_provider(name, args.chain, proxy=args.proxy, cache=not args.no_cache)
        except ProviderError as e:
            _log(f"[x] {e}")
            return 2
        labels = load_labels(args.labels, include_demo=(name == "demo"))
        if not args.labels and name != "demo":
            _log("[!] no --labels supplied: nothing will be attributed to any entity (all nodes 'unlabeled')")
        return _run(args, args.seeds, prov, labels)
    return 0


if __name__ == "__main__":
    sys.exit(main())
