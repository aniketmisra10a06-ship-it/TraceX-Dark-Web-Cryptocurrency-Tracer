"""Start-up banner."""
from __future__ import annotations

import os
import sys

from . import __version__

ART = r"""
 ████████╗██████╗  █████╗  ██████╗███████╗██╗  ██╗
 ╚══██╔══╝██╔══██╗██╔══██╗██╔════╝██╔════╝╚██╗██╔╝
    ██║   ██████╔╝███████║██║     █████╗   ╚███╔╝
    ██║   ██╔══██╗██╔══██║██║     ██╔══╝   ██╔██╗
    ██║   ██║  ██║██║  ██║╚██████╗███████╗██╔╝ ██╗
    ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝╚══════╝╚═╝  ╚═╝
"""
# cyan -> violet gradient (256-colour codes), one per art line
GRADIENT = [51, 45, 39, 75, 111, 141]


def _color_ok(stream) -> bool:
    return stream.isatty() and "NO_COLOR" not in os.environ and os.environ.get("TERM") != "dumb"


def render(color: bool = True) -> str:
    lines = ART.strip("\n").splitlines()
    out = []
    for i, ln in enumerate(lines):
        out.append(f"\033[1;38;5;{GRADIENT[i % len(GRADIENT)]}m{ln}\033[0m" if color else ln)
    sub = "  ⛓  Follow the money. Map the chain. Prove the path.  ⛓"
    by = f"  v{__version__}   ·   By Aniket Misra"
    note = "  Blockchain forensics · AML tracing · public-ledger data only"
    if color:
        sub, by, note = f"\033[1;38;5;220m{sub}\033[0m", f"\033[1;38;5;213m{by}\033[0m", f"\033[2m{note}\033[0m"
    rule = "  " + "━" * 62
    return "\n".join(out + ["", sub, by, note, rule, ""])


def print_banner(stream=None) -> None:
    stream = stream or sys.stderr
    try:
        stream.write(render(_color_ok(stream)) + "\n")
        stream.flush()
    except UnicodeEncodeError:   # legacy consoles
        stream.write(f"\nTraceX v{__version__} - By Aniket Misra\n\n")
