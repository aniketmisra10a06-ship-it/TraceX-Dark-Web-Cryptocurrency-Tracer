# Contributing to TraceX

1. Fork, create a branch, `pip install -e ".[dev]"`.
2. Add tests for behaviour changes; run `pytest` and `ruff check src tests`.
3. Read the secure-development rules in [SECURITY.md](SECURITY.md#5-secure-development-practices-for-contributors) - especially: no new runtime dependencies, sanitise every untrusted string for its output sink, never log secrets.
4. Never include real label data, API keys or victim information in issues or PRs. Use the synthetic demo scenario for reproductions.
5. Open a PR describing the change and any accuracy trade-offs of new heuristics.

Report security issues privately (see SECURITY.md), not as public issues.
