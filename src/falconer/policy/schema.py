"""Policy schema definitions for Falconer."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, validator


class Policy(BaseModel):
    """Policy configuration for spending limits and rules."""

    max_daily_spend_sats: int = Field(
        gt=0, description="Maximum daily spending in satoshis"
    )
    max_single_tx_sats: int = Field(
        gt=0, description="Maximum single transaction in satoshis"
    )
    allowed_destinations: List[str] = Field(
        default_factory=list, description="Allowed destination addresses"
    )
    max_fee_rate_sats_per_vbyte: Optional[int] = Field(
        None, description="Maximum fee rate in sats/vbyte"
    )
    require_confirmation: bool = Field(
        default=True, description="Require confirmation for transactions"
    )

    @validator("max_single_tx_sats")
    def single_tx_less_than_daily(cls, v, values):
        """Ensure single transaction limit is less than daily limit."""
        if "max_daily_spend_sats" in values and v > values["max_daily_spend_sats"]:
            raise ValueError(
                "max_single_tx_sats must be less than or equal to max_daily_spend_sats"
            )
        return v


class TransactionRequest(BaseModel):
    """Request for a Bitcoin transaction."""

    destination: str = Field(description="Destination address")
    amount_sats: int = Field(gt=0, description="Amount in satoshis")
    fee_rate_sats_per_vbyte: Optional[int] = Field(
        None, description="Fee rate in sats/vbyte"
    )
    description: Optional[str] = Field(None, description="Transaction description")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class PolicyViolation(BaseModel):
    """Represents a policy violation."""

    violation_type: str = Field(description="Type of violation")
    message: str = Field(description="Description of the violation")
    transaction_request: TransactionRequest = Field(
        description="The transaction that violated policy"
    )
    severity: str = Field(
        default="error", description="Severity level (warning, error, critical)"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="When the violation occurred"
    )


class DailySpend(BaseModel):
    """Daily spending tracking."""

    date: str = Field(description="Date in YYYY-MM-DD format")
    total_spent_sats: int = Field(ge=0, description="Total spent in satoshis")
    transaction_count: int = Field(ge=0, description="Number of transactions")

    @validator("date")
    def validate_date_format(cls, v):
        """Validate date format."""
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError:
            raise ValueError("Date must be in YYYY-MM-DD format")
        return v
