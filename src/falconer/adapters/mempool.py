# src/falconer/adapters/mempool.py
from __future__ import annotations

import os
from typing import Optional, Union

import httpx

from ..exceptions import MempoolAdapterError
from ..logging import get_logger

log = get_logger(__name__)


def _env(name: str, default: Optional[str] = None) -> Optional[str]:
    v = os.environ.get(name)
    return v if (v is not None and v != "") else default


class MempoolAdapter:
    """
    Minimal client for a Mempool/Esplora-compatible API.
    - Tries LAN first when MODE is 'auto' or 'lan'
    - Falls back to Tor when MODE is 'auto' or 'tor'
    - Does NOT call bitcoind.
    """

    def __init__(self) -> None:
        # Modes: auto | lan | tor
        self.mode = _env("MEMPOOL_MODE", "auto").lower()

        # LAN endpoint (scheme + host[:port]). Port defaults to 80 if omitted.
        lan_scheme = _env("MEMPOOL_LAN_SCHEME", "http")
        lan_host = _env("MEMPOOL_LAN_HOST_LOCAL")  # .local hostname
        lan_port = _env("MEMPOOL_LAN_PORT")  # may be None
        if lan_host:
            if lan_port:
                self.lan_base = f"{lan_scheme}://{lan_host}:{lan_port}"
            else:
                self.lan_base = f"{lan_scheme}://{lan_host}"
        else:
            self.lan_base = None

        # Tor endpoint (full URL incl. onion host, optional port)
        self.tor_base = _env("MEMPOOL_TOR_URL")

        # SOCKS proxy for Tor (e.g. socks5h://127.0.0.1:9050)
        self.tor_socks = _env("TOR_SOCKS_URL")

    async def _get_json(
        self, client: httpx.AsyncClient, url: str
    ) -> Union[dict, list, str, int]:
        r = await client.get(url)
        r.raise_for_status()
        ct = r.headers.get("content-type", "")
        if "application/json" in ct:
            return r.json()
        # Some endpoints (e.g. /api/blocks/tip/height) return plain text
        return r.text

    async def tip_height(self) -> int:
        """
        Query /api/blocks/tip/height and return an int.
        Tries LAN first (if configured and mode allows), then Tor.
        """
        path = "/api/blocks/tip/height"

        # Try LAN
        if self.mode in ("auto", "lan") and self.lan_base:
            url = f"{self.lan_base.rstrip('/')}{path}"
            try:
                async with httpx.AsyncClient(timeout=20) as c:
                    data = await self._get_json(c, url)
                log.info("Mempool tip via LAN", extra={"url": url})
                return int(data) if isinstance(data, str) else int(data)
            except Exception as e:
                log.warning(
                    "Mempool LAN failed, will try Tor if allowed",
                    extra={"error": str(e)},
                )

            if self.mode == "lan":
                raise MempoolAdapterError(f"Mempool LAN unreachable: {url}")

        # Try Tor
        if self.mode in ("auto", "tor"):
            if not self.tor_base:
                raise MempoolAdapterError(
                    "MEMPOOL_TOR_URL not set but mode requires Tor"
                )
            url = f"{self.tor_base.rstrip('/')}{path}"
            proxies = None
            if self.tor_socks:
                proxies = {"http": self.tor_socks, "https": self.tor_socks}
            async with httpx.AsyncClient(timeout=30, proxies=proxies) as c:
                data = await self._get_json(c, url)
            log.info("Mempool tip via Tor", extra={"url": url})
            return int(data) if isinstance(data, str) else int(data)

        raise MempoolAdapterError("Mempool unreachable (no LAN/Tor succeeded)")

    def close(self) -> None:
        # Placeholder for symmetry with other adapters
        pass
