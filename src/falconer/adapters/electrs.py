"""Electrs REST API adapter for Falconer."""

from typing import Any, Dict, List, Optional

import httpx
from pydantic import BaseModel

from ..config import Config
from ..exceptions import ElectrsAdapterError
from ..logging import get_logger

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
        self.client = httpx.Client(base_url=self.base_url, timeout=30.0)

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
        try:
            response = self.client.request(method, endpoint, **kwargs)
            response.raise_for_status()
            return response.json()

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

        Returns:
            Fee estimates for different confirmation targets
        """
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
