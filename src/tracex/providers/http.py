"""Small hardened HTTP client: TLS verification always on, rate limiting, retries, disk cache,
secrets kept out of cache keys and logs."""
from __future__ import annotations

import hashlib
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, Optional

from .. import __version__

DEFAULT_CACHE = Path(os.environ.get("TRACEX_CACHE_DIR", Path.home() / ".cache" / "tracex"))
MAX_BYTES = 20 * 1024 * 1024


class ProviderError(RuntimeError):
    pass


class HttpClient:
    def __init__(self, base_url: str, rate_per_sec: float = 3.0, retries: int = 4, timeout: int = 30,
                 cache: bool = True, cache_dir: Optional[Path] = None, proxy: Optional[str] = None) -> None:
        if not base_url.startswith("https://"):
            raise ProviderError("refusing non-HTTPS provider URL")
        self.base = base_url.rstrip("/")
        self.min_gap = 1.0 / rate_per_sec if rate_per_sec > 0 else 0
        self.retries = retries
        self.timeout = timeout
        self.cache = cache
        self.cache_dir = Path(cache_dir or DEFAULT_CACHE)
        self._last = 0.0
        handlers = []
        if proxy:
            handlers.append(urllib.request.ProxyHandler({"https": proxy, "http": proxy}))
        self._opener = urllib.request.build_opener(*handlers)
        self.requests_made = 0
        self.cache_hits = 0

    def _cache_path(self, key: str) -> Path:
        return self.cache_dir / (hashlib.sha256(key.encode()).hexdigest() + ".json")

    def get_json(self, path: str, params: Optional[Dict[str, Any]] = None,
                 secret_params: Optional[Dict[str, Any]] = None, ttl: int = 3600) -> Any:
        qs = urllib.parse.urlencode(params or {})
        public_url = f"{self.base}{path}" + (f"?{qs}" if qs else "")
        cp = self._cache_path(public_url)          # API keys are NOT part of the cache key
        if self.cache and cp.exists() and time.time() - cp.stat().st_mtime < ttl:
            self.cache_hits += 1
            return json.loads(cp.read_text())
        full = urllib.parse.urlencode({**(params or {}), **(secret_params or {})})
        url = f"{self.base}{path}" + (f"?{full}" if full else "")
        delay = 1.0
        last_err: Optional[Exception] = None
        for _ in range(self.retries):
            wait = self.min_gap - (time.time() - self._last)
            if wait > 0:
                time.sleep(wait)
            self._last = time.time()
            req = urllib.request.Request(url, headers={"User-Agent": f"TraceX/{__version__}",
                                                       "Accept": "application/json"})
            try:
                self.requests_made += 1
                with self._opener.open(req, timeout=self.timeout) as r:
                    raw = r.read(MAX_BYTES + 1)
                    if len(raw) > MAX_BYTES:
                        raise ProviderError("response too large")
                    data = json.loads(raw)
                if self.cache:
                    self.cache_dir.mkdir(parents=True, exist_ok=True)
                    cp.write_text(json.dumps(data))
                    os.chmod(cp, 0o600)
                return data
            except urllib.error.HTTPError as e:
                last_err = e
                if e.code in (429, 500, 502, 503, 504):
                    time.sleep(delay)
                    delay *= 2
                    continue
                raise ProviderError(f"HTTP {e.code} for {public_url}") from None   # no secrets in message
            except (urllib.error.URLError, TimeoutError) as e:
                last_err = e
                time.sleep(delay)
                delay *= 2
        raise ProviderError(f"request failed after retries: {public_url} ({type(last_err).__name__})")
