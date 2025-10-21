"""Integration tests for Falconer."""

import asyncio
from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from falconer.config import Config
from falconer.exceptions import AddressValidationError, PolicyViolationError
from falconer.persistence import PersistenceManager
from falconer.policy.engine import PolicyEngine
from falconer.policy.schema import Policy, TransactionRequest
from falconer.validation import validate_amount_sats, validate_bitcoin_address


class TestIntegration:
    """Integration tests for Falconer components."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = Config(
            max_daily_spend_sats=10000,
            max_single_tx_sats=5000,
            allowed_destinations=["bc1qtest1", "bc1qtest2"],
        )

        self.policy = Policy(
            max_daily_spend_sats=10000,
            max_single_tx_sats=5000,
            allowed_destinations=["bc1qtest1", "bc1qtest2"],
            max_fee_rate_sats_per_vbyte=50,
        )

        # Use in-memory persistence for testing
        self.persistence = PersistenceManager(data_dir="test_data")
        self.policy_engine = PolicyEngine(self.policy, self.persistence)

    def teardown_method(self):
        """Clean up test fixtures."""
        import os
        import shutil

        if os.path.exists("test_data"):
            shutil.rmtree("test_data")

    def test_policy_engine_with_persistence(self):
        """Test policy engine with persistence layer."""
        # Create a valid transaction request
        request = TransactionRequest(
            destination="bc1qtest1", amount_sats=1000, fee_rate_sats_per_vbyte=10
        )

        # Should pass validation
        violations = self.policy_engine.validate_transaction(request)
        assert len(violations) == 0

        # Record the transaction
        self.policy_engine.record_transaction(request, "test_txid")

        # Check that it was persisted
        today = datetime.utcnow().date().strftime("%Y-%m-%d")
        daily_spend = self.persistence.load_daily_spend(today)
        assert daily_spend is not None
        assert daily_spend.total_spent_sats == 1000
        assert daily_spend.transaction_count == 1

        # Check transaction history
        history = self.persistence.load_transaction_history()
        assert len(history) == 1
        assert history[0]["amount_sats"] == 1000
        assert history[0]["txid"] == "test_txid"

    def test_daily_spend_limit_enforcement(self):
        """Test that daily spend limits are enforced across restarts."""
        # First transaction
        request1 = TransactionRequest(destination="bc1qtest1", amount_sats=8000)

        # Should pass
        violations = self.policy_engine.validate_transaction(request1)
        assert len(violations) == 0

        # Record it
        self.policy_engine.record_transaction(request1, "tx1")

        # Second transaction that would exceed daily limit
        request2 = TransactionRequest(
            destination="bc1qtest1",
            amount_sats=3000,  # 8000 + 3000 = 11000 > 10000 limit
        )

        # Should fail
        violations = self.policy_engine.validate_transaction(request2)
        assert len(violations) == 1
        assert violations[0].violation_type == "daily_limit_exceeded"

        # Check that violation was logged
        violations_log = self.persistence.load_policy_violations()
        assert len(violations_log) == 1
        assert violations_log[0]["violation_type"] == "daily_limit_exceeded"

    def test_address_validation_integration(self):
        """Test address validation integration."""
        # Valid addresses
        valid_addresses = [
            "bc1qtest1",  # Test address
            "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",  # Genesis block
            "3J98t1WpEZ73CNmQviecrnyiWrnqRhWNLy",  # P2SH
        ]

        for address in valid_addresses:
            # Should not raise exception
            validate_bitcoin_address(address, network="testnet")

        # Invalid addresses
        invalid_addresses = ["invalid_address", "", "bc1qinvalid", "1invalid"]

        for address in invalid_addresses:
            with pytest.raises(AddressValidationError):
                validate_bitcoin_address(address)

    def test_amount_validation_integration(self):
        """Test amount validation integration."""
        # Valid amounts
        valid_amounts = [1, 100, 1000, 1000000, 2100000000000000]  # Max Bitcoin supply

        for amount in valid_amounts:
            assert validate_amount_sats(amount) is True

        # Invalid amounts
        invalid_amounts = [0, -1, 2100000000000001]  # Exceeds max supply

        for amount in invalid_amounts:
            with pytest.raises(ValueError):
                validate_amount_sats(amount)

    def test_policy_violation_logging(self):
        """Test that policy violations are properly logged."""
        # Create a transaction that violates policy
        request = TransactionRequest(
            destination="bc1qnotallowed",  # Not in allowed destinations
            amount_sats=6000,  # Exceeds single tx limit
            fee_rate_sats_per_vbyte=100,  # Exceeds fee rate limit
        )

        # Validate transaction
        violations = self.policy_engine.validate_transaction(request)

        # Should have multiple violations
        assert len(violations) == 3

        violation_types = [v.violation_type for v in violations]
        assert "destination_not_allowed" in violation_types
        assert "amount_limit_exceeded" in violation_types
        assert "fee_rate_exceeded" in violation_types

        # Check that all violations were logged
        logged_violations = self.persistence.load_policy_violations()
        assert len(logged_violations) == 3

        logged_types = [v["violation_type"] for v in logged_violations]
        assert "destination_not_allowed" in logged_types
        assert "amount_limit_exceeded" in logged_types
        assert "fee_rate_exceeded" in logged_types

    def test_transaction_history_persistence(self):
        """Test transaction history persistence."""
        # Create multiple transactions
        transactions = [
            TransactionRequest(
                destination="bc1qtest1", amount_sats=1000, description="Test 1"
            ),
            TransactionRequest(
                destination="bc1qtest2", amount_sats=2000, description="Test 2"
            ),
            TransactionRequest(
                destination="bc1qtest1", amount_sats=1500, description="Test 3"
            ),
        ]

        # Record all transactions
        for i, tx in enumerate(transactions):
            self.policy_engine.record_transaction(tx, f"txid_{i}")

        # Check history
        history = self.persistence.load_transaction_history()
        assert len(history) == 3

        # Check that all transactions are in history
        amounts = [tx["amount_sats"] for tx in history]
        assert 1000 in amounts
        assert 2000 in amounts
        assert 1500 in amounts

        # Check daily spend total
        today = datetime.utcnow().date().strftime("%Y-%m-%d")
        daily_spend = self.persistence.load_daily_spend(today)
        assert daily_spend.total_spent_sats == 4500  # 1000 + 2000 + 1500
        assert daily_spend.transaction_count == 3

    def test_data_cleanup(self):
        """Test data cleanup functionality."""
        # Create some old data
        old_date = "2020-01-01"
        old_spend = {"date": old_date, "total_spent_sats": 1000, "transaction_count": 1}

        # Manually add old data
        self.persistence._save_json(
            self.persistence.daily_spends_file, {old_date: old_spend}
        )

        # Run cleanup
        self.persistence.cleanup_old_data(days=30)

        # Check that old data was removed
        daily_spends = self.persistence._load_daily_spends()
        assert old_date not in daily_spends

    @pytest.mark.asyncio
    async def test_mempool_adapter_integration(self):
        """Test mempool adapter integration."""
        from falconer.adapters.mempool import MempoolAdapter

        # Mock the adapter to avoid actual network calls
        with patch("falconer.adapters.mempool.httpx.AsyncClient") as mock_client:
            mock_response = Mock()
            mock_response.text = "800000"  # Mock tip height
            mock_response.headers = {"content-type": "text/plain"}
            mock_response.raise_for_status.return_value = None

            mock_client.return_value.__aenter__.return_value.get.return_value = (
                mock_response
            )

            adapter = MempoolAdapter()
            tip_height = await adapter.tip_height()

            assert tip_height == 800000


class TestConfigurationIntegration:
    """Test configuration integration."""

    def test_config_validation(self):
        """Test configuration validation."""
        # Valid config
        config = Config(max_daily_spend_sats=10000, max_single_tx_sats=5000)
        assert config.max_daily_spend_sats == 10000
        assert config.max_single_tx_sats == 5000

        # Invalid config - single tx > daily limit
        with pytest.raises(
            ValueError,
            match="max_single_tx_sats must be less than or equal to max_daily_spend_sats",
        ):
            Config(max_daily_spend_sats=5000, max_single_tx_sats=10000)

    def test_allowed_destinations_parsing(self):
        """Test allowed destinations parsing from environment."""
        import os

        # Set environment variable
        os.environ["ALLOWED_DESTINATIONS"] = "bc1qtest1,bc1qtest2,bc1qtest3"

        try:
            config = Config()
            assert len(config.allowed_destinations) == 3
            assert "bc1qtest1" in config.allowed_destinations
            assert "bc1qtest2" in config.allowed_destinations
            assert "bc1qtest3" in config.allowed_destinations
        finally:
            # Clean up environment
            if "ALLOWED_DESTINATIONS" in os.environ:
                del os.environ["ALLOWED_DESTINATIONS"]
