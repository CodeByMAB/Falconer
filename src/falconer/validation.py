"""Validation utilities for Falconer."""

import re
from typing import List, Optional

from .exceptions import AddressValidationError


def validate_bitcoin_address(address: str, network: str = "mainnet") -> bool:
    """Validate a Bitcoin address.

    Args:
        address: Bitcoin address to validate
        network: Network type ("mainnet", "testnet", "regtest")

    Returns:
        True if address is valid

    Raises:
        AddressValidationError: If address is invalid
    """
    if not address or not isinstance(address, str):
        raise AddressValidationError("Address must be a non-empty string")

    # Basic format validation
    if len(address) < 26 or len(address) > 62:
        raise AddressValidationError("Address length is invalid")

    # Check for valid characters (Base58 for legacy, bech32 for native segwit)
    if not re.match(
        r"^[13][a-km-zA-HJ-NP-Z1-9]{25,34}$|^bc1[a-z0-9]{39,59}$|^tb1[a-z0-9]{39,59}$",
        address,
    ):
        raise AddressValidationError("Address format is invalid")

    # Network-specific validation
    if network == "mainnet":
        if (
            address.startswith("tb1")
            or address.startswith("2")
            or address.startswith("m")
            or address.startswith("n")
        ):
            raise AddressValidationError("Testnet address not allowed on mainnet")
    elif network == "testnet":
        if (
            address.startswith("bc1")
            or address.startswith("1")
            or address.startswith("3")
        ):
            raise AddressValidationError("Mainnet address not allowed on testnet")

    return True


def validate_bitcoin_addresses(
    addresses: List[str], network: str = "mainnet"
) -> List[str]:
    """Validate a list of Bitcoin addresses.

    Args:
        addresses: List of Bitcoin addresses to validate
        network: Network type ("mainnet", "testnet", "regtest")

    Returns:
        List of valid addresses

    Raises:
        AddressValidationError: If any address is invalid
    """
    valid_addresses = []
    for address in addresses:
        if validate_bitcoin_address(address, network):
            valid_addresses.append(address)
    return valid_addresses


def is_valid_bitcoin_address(address: str, network: str = "mainnet") -> bool:
    """Check if a Bitcoin address is valid without raising exceptions.

    Args:
        address: Bitcoin address to check
        network: Network type ("mainnet", "testnet", "regtest")

    Returns:
        True if address is valid, False otherwise
    """
    try:
        return validate_bitcoin_address(address, network)
    except AddressValidationError:
        return False


def validate_amount_sats(amount: int) -> bool:
    """Validate a Bitcoin amount in satoshis.

    Args:
        amount: Amount in satoshis

    Returns:
        True if amount is valid

    Raises:
        ValueError: If amount is invalid
    """
    if not isinstance(amount, int):
        raise ValueError("Amount must be an integer")

    if amount <= 0:
        raise ValueError("Amount must be positive")

    # Maximum Bitcoin supply in satoshis (21M BTC)
    max_sats = 21_000_000 * 100_000_000
    if amount > max_sats:
        raise ValueError("Amount exceeds maximum Bitcoin supply")

    return True


def validate_fee_rate(fee_rate: float) -> bool:
    """Validate a fee rate in sats/vbyte.

    Args:
        fee_rate: Fee rate in sats/vbyte

    Returns:
        True if fee rate is valid

    Raises:
        ValueError: If fee rate is invalid
    """
    if not isinstance(fee_rate, (int, float)):
        raise ValueError("Fee rate must be a number")

    if fee_rate <= 0:
        raise ValueError("Fee rate must be positive")

    # Reasonable upper limit (1000 sats/vbyte)
    if fee_rate > 1000:
        raise ValueError("Fee rate is unreasonably high")

    return True
