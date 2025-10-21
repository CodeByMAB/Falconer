"""Bitcoin Knots RPC adapter for Falconer."""

import json
from typing import Any, Dict, List, Optional

import httpx
from pydantic import BaseModel

from ..config import Config
from ..exceptions import BitcoinAdapterError, BitcoinRPCError
from ..logging import get_logger

logger = get_logger(__name__)


class BitcoinRPCResponse(BaseModel):
    """Bitcoin RPC response model."""

    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None
    id: Optional[str] = None


class BitcoinAdapter:
    """Adapter for Bitcoin Knots RPC interface."""

    def __init__(self, config: Config):
        """Initialize Bitcoin Knots adapter.

        Args:
            config: Falconer configuration
        """
        self.config = config
        self.base_url = config.bitcoind_url
        self.auth = (config.bitcoind_rpc_user, config.bitcoind_rpc_pass)
        self.client = httpx.Client(base_url=self.base_url, auth=self.auth, timeout=30.0)

    def _make_rpc_call(
        self, method: str, params: List[Any] = None
    ) -> BitcoinRPCResponse:
        """Make an RPC call to Bitcoin Knots.

        Args:
            method: RPC method name
            params: RPC method parameters

        Returns:
            Bitcoin RPC response

        Raises:
            Exception: If RPC call fails
        """
        if params is None:
            params = []

        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": "falconer",
        }

        try:
            response = self.client.post("/", json=payload)
            response.raise_for_status()

            data = response.json()
            rpc_response = BitcoinRPCResponse(**data)

            if rpc_response.error:
                raise BitcoinRPCError(f"Bitcoin Knots RPC error: {rpc_response.error}")

            return rpc_response

        except httpx.HTTPError as e:
            logger.error("Bitcoin Knots RPC HTTP error", error=str(e))
            raise BitcoinAdapterError(f"HTTP error connecting to Bitcoin Core: {e}")
        except Exception as e:
            logger.error("Bitcoin Knots RPC call failed", method=method, error=str(e))
            raise BitcoinAdapterError(f"RPC call failed for method {method}: {e}")

    def get_blockchain_info(self) -> Dict[str, Any]:
        """Get blockchain information.

        Returns:
            Blockchain information dictionary
        """
        response = self._make_rpc_call("getblockchaininfo")
        return response.result

    def get_network_info(self) -> Dict[str, Any]:
        """Get network information.

        Returns:
            Network information dictionary
        """
        response = self._make_rpc_call("getnetworkinfo")
        return response.result

    def get_mempool_info(self) -> Dict[str, Any]:
        """Get mempool information.

        Returns:
            Mempool information dictionary
        """
        response = self._make_rpc_call("getmempoolinfo")
        return response.result

    def estimate_smart_fee(self, target_blocks: int = 6) -> Dict[str, Any]:
        """Estimate smart fee for target number of blocks.

        Args:
            target_blocks: Target number of blocks for confirmation

        Returns:
            Fee estimation result
        """
        response = self._make_rpc_call("estimatesmartfee", [target_blocks])
        return response.result

    def get_raw_mempool(self, verbose: bool = False) -> List[Any]:
        """Get raw mempool transactions.

        Args:
            verbose: Whether to return verbose information

        Returns:
            List of mempool transaction IDs or verbose information
        """
        response = self._make_rpc_call("getrawmempool", [verbose])
        return response.result

    def get_transaction(self, txid: str, verbose: bool = True) -> Dict[str, Any]:
        """Get transaction information.

        Args:
            txid: Transaction ID
            verbose: Whether to return verbose information

        Returns:
            Transaction information
        """
        response = self._make_rpc_call("gettransaction", [txid, verbose])
        return response.result

    def get_balance(self, account: str = "*", minconf: int = 1) -> float:
        """Get wallet balance.

        Args:
            account: Account name (use "*" for all accounts)
            minconf: Minimum confirmations required

        Returns:
            Balance in BTC
        """
        response = self._make_rpc_call("getbalance", [account, minconf])
        return response.result

    def list_unspent(
        self, minconf: int = 1, maxconf: int = 9999999
    ) -> List[Dict[str, Any]]:
        """List unspent transaction outputs.

        Args:
            minconf: Minimum confirmations
            maxconf: Maximum confirmations

        Returns:
            List of unspent outputs
        """
        response = self._make_rpc_call("listunspent", [minconf, maxconf])
        return response.result

    def create_raw_transaction(
        self, inputs: List[Dict[str, Any]], outputs: Dict[str, float]
    ) -> str:
        """Create a raw transaction.

        Args:
            inputs: List of transaction inputs
            outputs: Dictionary of outputs (address: amount)

        Returns:
            Raw transaction hex string
        """
        response = self._make_rpc_call("createrawtransaction", [inputs, outputs])
        return response.result

    def sign_raw_transaction_with_wallet(self, hexstring: str) -> Dict[str, Any]:
        """Sign a raw transaction with wallet.

        Args:
            hexstring: Raw transaction hex string

        Returns:
            Signing result
        """
        response = self._make_rpc_call("signrawtransactionwithwallet", [hexstring])
        return response.result

    def send_raw_transaction(self, hexstring: str) -> str:
        """Send a raw transaction.

        Args:
            hexstring: Signed raw transaction hex string

        Returns:
            Transaction ID
        """
        response = self._make_rpc_call("sendrawtransaction", [hexstring])
        return response.result

    def close(self) -> None:
        """Close the HTTP client."""
        self.client.close()
