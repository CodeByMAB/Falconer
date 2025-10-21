"""LNbits API adapter for Falconer."""

from typing import Any, Dict, List, Optional

import httpx
from pydantic import BaseModel

from ..config import Config
from ..exceptions import LNbitsAdapterError
from ..logging import get_logger

logger = get_logger(__name__)


class LNbitsPayment(BaseModel):
    """LNbits payment model."""

    id: str
    payment_hash: str
    payment_request: str
    amount: int
    fee: int
    status: str
    time: int
    description: Optional[str] = None


class LNbitsInvoice(BaseModel):
    """LNbits invoice model."""

    payment_hash: str
    payment_request: str
    amount: int
    description: Optional[str] = None
    time: int


class LNbitsAdapter:
    """Adapter for LNbits API interface."""

    def __init__(self, config: Config):
        """Initialize LNbits adapter.

        Args:
            config: Falconer configuration
        """
        self.config = config
        self.base_url = config.lnbits_url
        self.api_key = config.lnbits_api_key
        self.wallet_id = config.lnbits_wallet_id

        self.client = httpx.Client(
            base_url=self.base_url,
            headers={"X-Api-Key": self.api_key, "Content-Type": "application/json"},
            timeout=30.0,
        )

    def _make_request(self, method: str, endpoint: str, **kwargs) -> Any:
        """Make a request to LNbits API.

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
            logger.error("LNbits API HTTP error", endpoint=endpoint, error=str(e))
            raise LNbitsAdapterError(f"HTTP error calling LNbits API {endpoint}: {e}")
        except Exception as e:
            logger.error("LNbits API call failed", endpoint=endpoint, error=str(e))
            raise LNbitsAdapterError(f"API call failed for {endpoint}: {e}")

    def get_wallet_balance(self) -> Dict[str, int]:
        """Get wallet balance.

        Returns:
            Wallet balance information
        """
        return self._make_request("GET", f"/api/v1/wallet/{self.wallet_id}")

    def create_invoice(
        self, amount: int, description: Optional[str] = None
    ) -> LNbitsInvoice:
        """Create a lightning invoice.

        Args:
            amount: Invoice amount in satoshis
            description: Invoice description

        Returns:
            Created invoice
        """
        data = {
            "out": False,
            "amount": amount,
            "description": description or "Falconer invoice",
        }

        response = self._make_request("POST", "/api/v1/payments", json=data)
        return LNbitsInvoice(**response)

    def pay_invoice(self, payment_request: str) -> LNbitsPayment:
        """Pay a lightning invoice.

        Args:
            payment_request: Lightning payment request

        Returns:
            Payment information
        """
        data = {"out": True, "bolt11": payment_request}

        response = self._make_request("POST", "/api/v1/payments", json=data)
        return LNbitsPayment(**response)

    def get_payment_status(self, payment_hash: str) -> Dict[str, Any]:
        """Get payment status.

        Args:
            payment_hash: Payment hash

        Returns:
            Payment status information
        """
        return self._make_request("GET", f"/api/v1/payments/{payment_hash}")

    def get_payments(self, limit: int = 10, offset: int = 0) -> List[Dict[str, Any]]:
        """Get payment history.

        Args:
            limit: Maximum number of payments to return
            offset: Number of payments to skip

        Returns:
            List of payments
        """
        params = {"limit": limit, "offset": offset}
        return self._make_request("GET", "/api/v1/payments", params=params)

    def decode_invoice(self, payment_request: str) -> Dict[str, Any]:
        """Decode a lightning invoice.

        Args:
            payment_request: Lightning payment request

        Returns:
            Decoded invoice information
        """
        data = {"data": payment_request}
        return self._make_request("POST", "/api/v1/payments/decode", json=data)

    def get_lnurl_info(self, lnurl: str) -> Dict[str, Any]:
        """Get LNURL information.

        Args:
            lnurl: LNURL string

        Returns:
            LNURL information
        """
        return self._make_request("GET", f"/api/v1/lnurl/{lnurl}")

    def pay_lnurl(
        self, lnurl: str, amount: int, comment: Optional[str] = None
    ) -> Dict[str, Any]:
        """Pay via LNURL.

        Args:
            lnurl: LNURL string
            amount: Amount in satoshis
            comment: Optional comment

        Returns:
            Payment result
        """
        data = {"lnurl": lnurl, "amount": amount, "comment": comment}
        return self._make_request("POST", "/api/v1/lnurl/pay", json=data)

    def get_extension_info(self, extension: str) -> Dict[str, Any]:
        """Get extension information.

        Args:
            extension: Extension name

        Returns:
            Extension information
        """
        return self._make_request("GET", f"/api/v1/extensions/{extension}")

    def close(self) -> None:
        """Close the HTTP client."""
        self.client.close()
