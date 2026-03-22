# src/falconer/adapters/mempool.py
from __future__ import annotations

import os
from typing import Optional, Union

import httpx

from ..exceptions import MempoolAdapterError
from ..logging import get_logger
from ..utils import retry_on_network_error

log = get_logger(__name__)


def _env(name: str, default: Optional[str] = None) -> Optional[str]:
    v = os.environ.get(name)
    return v if (v is not None and v != "") else default


class MempoolAdapter:
    """
    Client for a Mempool/Esplora-compatible REST API.

    Reads configuration from environment variables:
      MEMPOOL_BASE_URL   — full base URL, e.g. https://mempool.space or http://host.onion
      MEMPOOL_USE_TOR    — "true" / "1" to route via SOCKS5
      TOR_SOCKS_PROXY    — SOCKS5 proxy URL, e.g. socks5h://127.0.0.1:9050

    Legacy env vars (MEMPOOL_LAN_HOST_LOCAL, MEMPOOL_TOR_URL, MEMPOOL_MODE) are still
    supported as fallback when MEMPOOL_BASE_URL is not set.
    """

    def __init__(self) -> None:
        # Primary: new-style MEMPOOL_BASE_URL
        self._base_url: Optional[str] = _env("MEMPOOL_BASE_URL")

        # Tor routing
        use_tor_raw = _env("MEMPOOL_USE_TOR", "false")
        self._use_tor: bool = str(use_tor_raw).lower() in ("true", "1", "yes")
        self._tor_proxy: Optional[str] = _env("TOR_SOCKS_PROXY", _env("TOR_SOCKS_URL", "socks5h://127.0.0.1:9050"))

        # Legacy: build base_url from old env vars when new-style not set
        if not self._base_url:
            self.mode = _env("MEMPOOL_MODE", "auto").lower()
            lan_scheme = _env("MEMPOOL_LAN_SCHEME", "http")
            lan_host = _env("MEMPOOL_LAN_HOST_LOCAL")
            lan_port = _env("MEMPOOL_LAN_PORT")
            tor_base = _env("MEMPOOL_TOR_URL")
            if lan_host:
                self._base_url = f"{lan_scheme}://{lan_host}:{lan_port}" if lan_port else f"{lan_scheme}://{lan_host}"
            elif tor_base:
                self._base_url = tor_base
                self._use_tor = True
            else:
                self._base_url = "https://mempool.space"
        else:
            self.mode = "tor" if self._use_tor else "custom"

        # Auto-detect Tor from .onion hostname
        if self._base_url and ".onion" in self._base_url:
            self._use_tor = True

    def _client_kwargs(self, timeout: int = 20) -> dict:
        """Build httpx.Client kwargs with SSL bypass and optional Tor proxy."""
        kw: dict = {"timeout": timeout, "verify": False, "follow_redirects": True}
        if self._use_tor and self._tor_proxy:
            kw["proxy"] = self._tor_proxy
        return kw

    def _url(self, path: str) -> str:
        base = (self._base_url or "https://mempool.space").rstrip("/")
        return f"{base}{path}"

    # ── Sync methods (used by dashboard health check) ─────────────────────────

    def get_fee_estimates(self) -> dict:
        """GET /api/v1/fees/recommended → {fastestFee, halfHourFee, hourFee, ...}"""
        url = self._url("/api/v1/fees/recommended")
        try:
            with httpx.Client(**self._client_kwargs()) as c:
                r = c.get(url)
                r.raise_for_status()
                return r.json()
        except httpx.HTTPError as e:
            log.error("Mempool fee estimates HTTP error", url=url, error=str(e))
            raise MempoolAdapterError(f"HTTP error fetching Mempool fee estimates: {e}")
        except Exception as e:
            log.error("Mempool fee estimates failed", url=url, error=str(e))
            raise MempoolAdapterError(f"Mempool fee estimates failed: {e}")

    def get_tip_height_sync(self) -> int:
        """GET /api/blocks/tip/height → block height (sync version)."""
        url = self._url("/api/blocks/tip/height")
        try:
            with httpx.Client(**self._client_kwargs()) as c:
                r = c.get(url)
                r.raise_for_status()
                return int(r.text.strip())
        except httpx.HTTPError as e:
            log.error("Mempool tip height HTTP error", url=url, error=str(e))
            raise MempoolAdapterError(f"HTTP error fetching Mempool tip height: {e}")
        except Exception as e:
            log.error("Mempool tip height failed", url=url, error=str(e))
            raise MempoolAdapterError(f"Mempool tip height failed: {e}")

    # ── Async methods (used by CLI / market analyzer) ─────────────────────────

    async def _get_json(
        self, client: httpx.AsyncClient, url: str
    ) -> Union[dict, list, str, int]:
        r = await client.get(url)
        r.raise_for_status()
        ct = r.headers.get("content-type", "")
        if "application/json" in ct:
            return r.json()
        return r.text

    @retry_on_network_error(max_attempts=3, base_delay=2.0)
    async def tip_height(self) -> int:
        """
        Async version for CLI / market_analyzer compatibility.
        Queries /api/blocks/tip/height and returns an int.
        """
        path = "/api/blocks/tip/height"
        url = self._url(path)
        async_kwargs: dict = {"timeout": 30, "verify": False}
        if self._use_tor and self._tor_proxy:
            async_kwargs["proxy"] = self._tor_proxy
        async with httpx.AsyncClient(**async_kwargs) as c:
            data = await self._get_json(c, url)
        log.info("Mempool tip height fetched", url=url)
        return int(data) if isinstance(data, str) else int(data)

    def close(self) -> None:
        pass
