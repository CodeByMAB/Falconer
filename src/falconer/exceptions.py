"""Custom exceptions for Falconer."""


class FalconerError(Exception):
    """Base exception for all Falconer errors."""

    pass


class ConfigurationError(FalconerError):
    """Raised when there's a configuration error."""

    pass


class BitcoinRPCError(FalconerError):
    """Raised when Bitcoin RPC calls fail."""

    pass


class PolicyViolationError(FalconerError):
    """Raised when a transaction violates policy rules."""

    def __init__(self, message: str, violations: list = None):
        super().__init__(message)
        self.violations = violations or []


class InsufficientFundsError(FalconerError):
    """Raised when there are insufficient funds for a transaction."""

    pass


class AddressValidationError(FalconerError):
    """Raised when Bitcoin address validation fails."""

    pass


class PSBTError(FalconerError):
    """Raised when PSBT operations fail."""

    pass


class NetworkError(FalconerError):
    """Raised when network operations fail."""

    pass


class AdapterError(FalconerError):
    """Base exception for adapter errors."""

    pass


class BitcoinAdapterError(AdapterError):
    """Raised when Bitcoin adapter operations fail."""

    pass


class ElectrsAdapterError(AdapterError):
    """Raised when Electrs adapter operations fail."""

    pass


class LNbitsAdapterError(AdapterError):
    """Raised when LNbits adapter operations fail."""

    pass


class MempoolAdapterError(AdapterError):
    """Raised when Mempool adapter operations fail."""

    pass
