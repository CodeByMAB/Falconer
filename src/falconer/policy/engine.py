"""Policy engine for enforcing spending limits and transaction rules."""

from datetime import datetime, timedelta
from typing import List, Optional

from ..logging import get_logger
from .schema import DailySpend, Policy, PolicyViolation, TransactionRequest

logger = get_logger(__name__)


class PolicyEngine:
    """Engine for enforcing spending policies and limits."""

    def __init__(self, policy: Policy, persistence_manager=None):
        """Initialize the policy engine.

        Args:
            policy: Policy configuration to enforce
            persistence_manager: Optional persistence manager for data storage
        """
        self.policy = policy
        self.persistence = persistence_manager
        self.daily_spends: List[DailySpend] = []

    def validate_transaction(
        self, request: TransactionRequest
    ) -> List[PolicyViolation]:
        """Validate a transaction request against the policy.

        Args:
            request: Transaction request to validate

        Returns:
            List of policy violations (empty if valid)
        """
        violations = []

        # Check single transaction limit
        if request.amount_sats > self.policy.max_single_tx_sats:
            violation = PolicyViolation(
                violation_type="amount_limit_exceeded",
                message=f"Transaction amount {request.amount_sats} sats exceeds single transaction limit of {self.policy.max_single_tx_sats} sats",
                transaction_request=request,
                severity="error",
            )
            violations.append(violation)

            # Log violation if persistence is available
            if self.persistence:
                self.persistence.save_policy_violation(violation.model_dump())

        # Check daily spending limit
        today_spent = self._get_daily_spend(datetime.utcnow().date())
        if today_spent + request.amount_sats > self.policy.max_daily_spend_sats:
            violation = PolicyViolation(
                violation_type="daily_limit_exceeded",
                message=f"Transaction would exceed daily spending limit. Today: {today_spent} sats, Request: {request.amount_sats} sats, Limit: {self.policy.max_daily_spend_sats} sats",
                transaction_request=request,
                severity="error",
            )
            violations.append(violation)

            # Log violation if persistence is available
            if self.persistence:
                self.persistence.save_policy_violation(violation.model_dump())

        # Check allowed destinations
        if (
            self.policy.allowed_destinations
            and request.destination not in self.policy.allowed_destinations
        ):
            violation = PolicyViolation(
                violation_type="destination_not_allowed",
                message=f"Destination {request.destination} is not in the allowed destinations list",
                transaction_request=request,
                severity="error",
            )
            violations.append(violation)

            # Log violation if persistence is available
            if self.persistence:
                self.persistence.save_policy_violation(violation.model_dump())

        # Check fee rate limit
        if (
            self.policy.max_fee_rate_sats_per_vbyte
            and request.fee_rate_sats_per_vbyte
            and request.fee_rate_sats_per_vbyte
            > self.policy.max_fee_rate_sats_per_vbyte
        ):
            violation = PolicyViolation(
                violation_type="fee_rate_exceeded",
                message=f"Fee rate {request.fee_rate_sats_per_vbyte} sats/vbyte exceeds limit of {self.policy.max_fee_rate_sats_per_vbyte} sats/vbyte",
                transaction_request=request,
                severity="warning",
            )
            violations.append(violation)

            # Log violation (warnings are also logged)
            self.persistence.save_policy_violation(violation.dict())

        return violations

    def record_transaction(
        self, request: TransactionRequest, txid: Optional[str] = None
    ) -> None:
        """Record a completed transaction for daily spending tracking.

        Args:
            request: Completed transaction request
            txid: Transaction ID if available
        """
        today = datetime.utcnow().date()
        today_str = today.strftime("%Y-%m-%d")

        if self.persistence:
            # Load existing daily spend or create new one
            daily_spend = self.persistence.load_daily_spend(today_str)

            if daily_spend is None:
                daily_spend = DailySpend(
                    date=today_str, total_spent_sats=0, transaction_count=0
                )

            # Update spending record
            daily_spend.total_spent_sats += request.amount_sats
            daily_spend.transaction_count += 1

            # Save to persistence
            self.persistence.save_daily_spend(daily_spend)

            # Also save transaction to history
            self.persistence.save_transaction(request, txid)
        else:
            # Fallback to in-memory storage
            daily_spend = None
            for spend in self.daily_spends:
                if spend.date == today_str:
                    daily_spend = spend
                    break

            if daily_spend is None:
                daily_spend = DailySpend(
                    date=today_str, total_spent_sats=0, transaction_count=0
                )
                self.daily_spends.append(daily_spend)

            # Update spending record
            daily_spend.total_spent_sats += request.amount_sats
            daily_spend.transaction_count += 1

        logger.info(
            "Transaction recorded",
            date=today_str,
            amount=request.amount_sats,
            txid=txid,
            daily_total=daily_spend.total_spent_sats,
        )

    def _get_daily_spend(self, date: datetime.date) -> int:
        """Get total spending for a specific date.

        Args:
            date: Date to check

        Returns:
            Total spending in satoshis for the date
        """
        date_str = date.strftime("%Y-%m-%d")

        if self.persistence:
            daily_spend = self.persistence.load_daily_spend(date_str)
            return daily_spend.total_spent_sats if daily_spend else 0
        else:
            # Fallback to in-memory storage
            for spend in self.daily_spends:
                if spend.date == date_str:
                    return spend.total_spent_sats
            return 0

    def get_daily_spend_summary(self, days: int = 7) -> List[DailySpend]:
        """Get daily spending summary for the last N days.

        Args:
            days: Number of days to include in summary

        Returns:
            List of daily spending records
        """
        if self.persistence:
            return self.persistence.load_daily_spends(days)
        else:
            # Fallback to in-memory storage
            cutoff_date = datetime.utcnow().date() - timedelta(days=days)
            return [
                spend
                for spend in self.daily_spends
                if datetime.strptime(spend.date, "%Y-%m-%d").date() >= cutoff_date
            ]

    def is_transaction_allowed(self, request: TransactionRequest) -> bool:
        """Check if a transaction is allowed under current policy.

        Args:
            request: Transaction request to check

        Returns:
            True if transaction is allowed, False otherwise
        """
        violations = self.validate_transaction(request)
        return len(violations) == 0
