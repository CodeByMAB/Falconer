"""Electrs REST API adapter for Falconer."""

import os
from typing import Any, Dict, List, Optional

import httpx
from pydantic import BaseModel

from ..config import Config
from ..exceptions import ElectrsAdapterError
from ..logging import get_logger
from ..utils import retry_on_network_error

logger = get_logger(__name__)


class ElectrsAdapter:
    """Adapter for Electrs REST API interface."""

    def __init__(self, config: Config):
        """Initialize Electrs adapter.

        Args:
            config: Falconer configuration
        """
        self.config = config
        self.base_url = config.electrs_url
        self.api_prefix: str = getattr(config, "electrs_api_prefix", "")

        use_tor = getattr(config, "electrs_use_tor", False)
        tor_proxy = getattr(config, "tor_socks_proxy", None) or os.environ.get(
            "TOR_SOCKS_PROXY", "socks5h://127.0.0.1:9050"
        )

        client_kwargs: Dict[str, Any] = {
            "base_url": self.base_url,
            "timeout": 30.0,
            "verify": False,
            "follow_redirects": True,
        }
        if use_tor:
            client_kwargs["proxy"] = tor_proxy

        self.client = httpx.Client(**client_kwargs)

    @retry_on_network_error(max_attempts=3, base_delay=2.0)
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Any:
        """Make a request to Electrs API.

        Args:
            method: HTTP method
            endpoint: API endpoint
            **kwargs: Additional request parameters

        Returns:
            API response data

        Raises:
            Exception: If request fails
        """
        full_endpoint = f"{self.api_prefix}{endpoint}"
        try:
            response = self.client.request(method, full_endpoint, **kwargs)
            response.raise_for_status()
            return response.json()

        except httpx.RemoteProtocolError:
            port = getattr(self.config, "electrs_port", "?")
            logger.error("Electrs protocol mismatch", endpoint=endpoint, port=port)
            raise ElectrsAdapterError(
                f"Protocol mismatch on {endpoint} — port {port} appears to be "
                "an Electrum TCP port (50001/50002), not the HTTP REST API. "
                "Re-run the Setup Wizard and enter the REST API .onion address from "
                "Start9 → Services → Electrs → Interfaces."
            )
        except httpx.HTTPError as e:
            logger.error("Electrs API HTTP error", endpoint=endpoint, error=str(e))
            raise ElectrsAdapterError(f"HTTP error calling Electrs API {endpoint}: {e}")
        except Exception as e:
            logger.error("Electrs API call failed", endpoint=endpoint, error=str(e))
            raise ElectrsAdapterError(f"API call failed for {endpoint}: {e}")

    def get_address_info(self, address: str) -> Dict[str, Any]:
        """Get address information.

        Args:
            address: Bitcoin address

        Returns:
            Address information
        """
        return self._make_request("GET", f"/address/{address}")

    def get_address_transactions(self, address: str) -> List[Dict[str, Any]]:
        """Get address transaction history.

        Args:
            address: Bitcoin address

        Returns:
            List of transactions
        """
        return self._make_request("GET", f"/address/{address}/txs")

    def get_address_utxos(self, address: str) -> List[Dict[str, Any]]:
        """Get address UTXOs.

        Args:
            address: Bitcoin address

        Returns:
            List of UTXOs
        """
        return self._make_request("GET", f"/address/{address}/utxo")

    def get_transaction(self, txid: str) -> Dict[str, Any]:
        """Get transaction information.

        Args:
            txid: Transaction ID

        Returns:
            Transaction information
        """
        return self._make_request("GET", f"/tx/{txid}")

    def get_transaction_hex(self, txid: str) -> str:
        """Get raw transaction hex.

        Args:
            txid: Transaction ID

        Returns:
            Raw transaction hex string
        """
        return self._make_request("GET", f"/tx/{txid}/hex")

    def get_transaction_status(self, txid: str) -> Dict[str, Any]:
        """Get transaction status.

        Args:
            txid: Transaction ID

        Returns:
            Transaction status
        """
        return self._make_request("GET", f"/tx/{txid}/status")

    def get_block(self, block_hash: str) -> Dict[str, Any]:
        """Get block information.

        Args:
            block_hash: Block hash

        Returns:
            Block information
        """
        return self._make_request("GET", f"/block/{block_hash}")

    def get_block_header(self, block_hash: str) -> str:
        """Get block header.

        Args:
            block_hash: Block hash

        Returns:
            Block header hex string
        """
        return self._make_request("GET", f"/block/{block_hash}/header")

    def get_block_transactions(self, block_hash: str) -> List[str]:
        """Get block transaction IDs.

        Args:
            block_hash: Block hash

        Returns:
            List of transaction IDs
        """
        return self._make_request("GET", f"/block/{block_hash}/txids")

    def get_tip_height(self) -> int:
        """Get current tip height.

        Returns:
            Current blockchain height
        """
        return self._make_request("GET", "/blocks/tip/height")

    def get_tip_hash(self) -> str:
        """Get current tip hash.

        Returns:
            Current tip block hash
        """
        return self._make_request("GET", "/blocks/tip/hash")

    def get_fee_estimates(self) -> Dict[str, float]:
        """Get fee estimates.

        In direct Electrs mode returns a dict keyed by block target (e.g. {"1": 20, "6": 5}).
        In Esplora/Mempool mode queries /api/v1/fees/recommended and converts to the same shape.
        """
        if self.api_prefix == "/api":
            data = self._make_request("GET", "/v1/fees/recommended")
            return {
                "1": float(data.get("fastestFee", 1)),
                "3": float(data.get("halfHourFee", 1)),
                "6": float(data.get("hourFee", 1)),
            }
        return self._make_request("GET", "/fee-estimates")

    def broadcast_transaction(self, hexstring: str) -> str:
        """Broadcast a raw transaction.

        Args:
            hexstring: Raw transaction hex string

        Returns:
            Transaction ID
        """
        return self._make_request("POST", "/tx", content=hexstring)

    def close(self) -> None:
        """Close the HTTP client."""
        self.client.close()
