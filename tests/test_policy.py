"""Tests for Falconer policy engine."""

from datetime import datetime

import pytest

from falconer.persistence import PersistenceManager
from falconer.policy.engine import PolicyEngine
from falconer.policy.schema import DailySpend, Policy, TransactionRequest


class TestPolicyEngine:
    """Test cases for PolicyEngine."""

    def setup_method(self):
        """Set up test fixtures."""
        import shutil
        import tempfile

        # Create a temporary directory for each test
        self.temp_dir = tempfile.mkdtemp()

        self.policy = Policy(
            max_daily_spend_sats=10000,
            max_single_tx_sats=5000,
            allowed_destinations=["bc1qtest1", "bc1qtest2"],
            max_fee_rate_sats_per_vbyte=50,
        )
        self.persistence = PersistenceManager(data_dir=self.temp_dir)
        self.engine = PolicyEngine(self.policy, self.persistence)

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        if hasattr(self, "temp_dir"):
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_valid_transaction(self):
        """Test that valid transactions pass policy validation."""
        request = TransactionRequest(
            destination="bc1qtest1", amount_sats=1000, fee_rate_sats_per_vbyte=10
        )

        violations = self.engine.validate_transaction(request)
        assert len(violations) == 0

    def test_amount_limit_exceeded(self):
        """Test that transactions exceeding single tx limit are rejected."""
        request = TransactionRequest(
            destination="bc1qtest1",
            amount_sats=6000,  # Exceeds max_single_tx_sats of 5000
            fee_rate_sats_per_vbyte=10,
        )

        violations = self.engine.validate_transaction(request)
        assert len(violations) == 1
        assert violations[0].violation_type == "amount_limit_exceeded"
        assert violations[0].severity == "error"

    def test_daily_limit_exceeded(self):
        """Test that transactions exceeding daily limit are rejected."""
        # First, record some spending
        request1 = TransactionRequest(destination="bc1qtest1", amount_sats=8000)
        self.engine.record_transaction(request1)

        # Now try to spend more than the remaining daily limit
        request2 = TransactionRequest(
            destination="bc1qtest1",
            amount_sats=3000,  # Would exceed daily limit of 10000
        )

        violations = self.engine.validate_transaction(request2)
        assert len(violations) == 1
        assert violations[0].violation_type == "daily_limit_exceeded"
        assert violations[0].severity == "error"

    def test_destination_not_allowed(self):
        """Test that transactions to non-allowed destinations are rejected."""
        request = TransactionRequest(
            destination="bc1qnotallowed", amount_sats=1000, fee_rate_sats_per_vbyte=10
        )

        violations = self.engine.validate_transaction(request)
        assert len(violations) == 1
        assert violations[0].violation_type == "destination_not_allowed"
        assert violations[0].severity == "error"

    def test_fee_rate_exceeded(self):
        """Test that transactions with excessive fee rates are flagged."""
        request = TransactionRequest(
            destination="bc1qtest1",
            amount_sats=1000,
            fee_rate_sats_per_vbyte=100,  # Exceeds max_fee_rate_sats_per_vbyte of 50
        )

        violations = self.engine.validate_transaction(request)
        assert len(violations) == 1
        assert violations[0].violation_type == "fee_rate_exceeded"
        assert violations[0].severity == "warning"

    def test_multiple_violations(self):
        """Test that multiple policy violations are detected."""
        request = TransactionRequest(
            destination="bc1qnotallowed",  # Not allowed
            amount_sats=6000,  # Exceeds single tx limit
            fee_rate_sats_per_vbyte=100,  # Exceeds fee rate limit
        )

        violations = self.engine.validate_transaction(request)
        # Should have multiple violations (amount, destination, fee rate)
        # Note: daily limit not triggered since we start with clean state
        assert len(violations) == 3

        violation_types = [v.violation_type for v in violations]
        assert "destination_not_allowed" in violation_types
        assert "amount_limit_exceeded" in violation_types
        assert "fee_rate_exceeded" in violation_types

    def test_daily_spend_tracking(self):
        """Test daily spending tracking functionality."""
        # Record multiple transactions
        request1 = TransactionRequest(destination="bc1qtest1", amount_sats=2000)
        request2 = TransactionRequest(destination="bc1qtest2", amount_sats=3000)

        self.engine.record_transaction(request1)
        self.engine.record_transaction(request2)

        # Check daily spend summary
        summary = self.engine.get_daily_spend_summary()
        assert len(summary) == 1

        today_spend = summary[0]
        assert today_spend.total_spent_sats == 5000
        assert today_spend.transaction_count == 2

    def test_is_transaction_allowed(self):
        """Test the is_transaction_allowed convenience method."""
        # Valid transaction
        valid_request = TransactionRequest(destination="bc1qtest1", amount_sats=1000)
        assert self.engine.is_transaction_allowed(valid_request) is True

        # Invalid transaction
        invalid_request = TransactionRequest(
            destination="bc1qnotallowed", amount_sats=1000
        )
        assert self.engine.is_transaction_allowed(invalid_request) is False

    def test_empty_allowed_destinations(self):
        """Test that empty allowed destinations list allows all destinations."""
        policy = Policy(
            max_daily_spend_sats=10000,
            max_single_tx_sats=5000,
            allowed_destinations=[],  # Empty list
        )
        engine = PolicyEngine(policy)

        request = TransactionRequest(destination="bc1qanydestination", amount_sats=1000)

        violations = engine.validate_transaction(request)
        assert len(violations) == 0

    def test_no_fee_rate_limit(self):
        """Test that no fee rate limit allows any fee rate."""
        policy = Policy(
            max_daily_spend_sats=10000,
            max_single_tx_sats=5000,
            max_fee_rate_sats_per_vbyte=None,  # No limit
        )
        engine = PolicyEngine(policy)

        request = TransactionRequest(
            destination="bc1qtest1",
            amount_sats=1000,
            fee_rate_sats_per_vbyte=1000,  # Very high fee rate
        )

        violations = engine.validate_transaction(request)
        assert len(violations) == 0


class TestPolicySchema:
    """Test cases for policy schema validation."""

    def test_policy_validation(self):
        """Test policy schema validation."""
        # Valid policy
        policy = Policy(
            max_daily_spend_sats=10000,
            max_single_tx_sats=5000,
            allowed_destinations=["bc1qtest1"],
        )
        assert policy.max_daily_spend_sats == 10000
        assert policy.max_single_tx_sats == 5000

    def test_single_tx_less_than_daily(self):
        """Test that single tx limit must be less than daily limit."""
        with pytest.raises(
            ValueError,
            match="max_single_tx_sats must be less than or equal to max_daily_spend_sats",
        ):
            Policy(
                max_daily_spend_sats=5000,
                max_single_tx_sats=10000,  # Exceeds daily limit
            )

    def test_positive_amounts(self):
        """Test that amounts must be positive."""
        with pytest.raises(ValueError):
            Policy(max_daily_spend_sats=-1000, max_single_tx_sats=5000)  # Negative

        with pytest.raises(ValueError):
            Policy(max_daily_spend_sats=10000, max_single_tx_sats=-5000)  # Negative

    def test_transaction_request_validation(self):
        """Test transaction request validation."""
        # Valid request
        request = TransactionRequest(destination="bc1qtest1", amount_sats=1000)
        assert request.destination == "bc1qtest1"
        assert request.amount_sats == 1000

        # Invalid amount
        with pytest.raises(ValueError):
            TransactionRequest(
                destination="bc1qtest1", amount_sats=-1000  # Negative amount
            )

    def test_daily_spend_validation(self):
        """Test daily spend validation."""
        # Valid daily spend
        spend = DailySpend(
            date="2024-01-01", total_spent_sats=1000, transaction_count=5
        )
        assert spend.date == "2024-01-01"
        assert spend.total_spent_sats == 1000

        # Invalid date format
        with pytest.raises(ValueError, match="Date must be in YYYY-MM-DD format"):
            DailySpend(
                date="01/01/2024",  # Wrong format
                total_spent_sats=1000,
                transaction_count=5,
            )

        # Negative amounts
        with pytest.raises(ValueError):
            DailySpend(
                date="2024-01-01",
                total_spent_sats=-1000,  # Negative
                transaction_count=5,
            )

        with pytest.raises(ValueError):
            DailySpend(
                date="2024-01-01",
                total_spent_sats=1000,
                transaction_count=-5,  # Negative
            )
