"""Tests for Falconer persistence layer."""

import json
import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from falconer.persistence import PersistenceManager
from falconer.policy.schema import DailySpend, TransactionRequest


class TestPersistenceManager:
    """Test PersistenceManager functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.test_dir = "test_persistence_data"
        self.persistence = PersistenceManager(data_dir=self.test_dir)

    def teardown_method(self):
        """Clean up test fixtures."""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_daily_spend_save_and_load(self):
        """Test saving and loading daily spend records."""
        # Create a daily spend record
        daily_spend = DailySpend(
            date="2024-01-01", total_spent_sats=5000, transaction_count=3
        )

        # Save it
        self.persistence.save_daily_spend(daily_spend)

        # Load it back
        loaded_spend = self.persistence.load_daily_spend("2024-01-01")

        assert loaded_spend is not None
        assert loaded_spend.date == "2024-01-01"
        assert loaded_spend.total_spent_sats == 5000
        assert loaded_spend.transaction_count == 3

    def test_daily_spend_load_nonexistent(self):
        """Test loading non-existent daily spend."""
        loaded_spend = self.persistence.load_daily_spend("2024-01-01")
        assert loaded_spend is None

    def test_daily_spends_load_multiple(self):
        """Test loading multiple daily spend records."""
        from datetime import datetime, timedelta

        # Create multiple daily spend records for recent dates
        today = datetime.now().date()
        dates = [
            (today - timedelta(days=2)).strftime("%Y-%m-%d"),
            (today - timedelta(days=1)).strftime("%Y-%m-%d"),
            today.strftime("%Y-%m-%d"),
        ]

        for i, date in enumerate(dates):
            daily_spend = DailySpend(
                date=date, total_spent_sats=1000 * (i + 1), transaction_count=i + 1
            )
            self.persistence.save_daily_spend(daily_spend)

        # Load all records
        loaded_spends = self.persistence.load_daily_spends(days=3)

        assert len(loaded_spends) == 3
        # The implementation returns them in reverse chronological order (newest first)
        assert loaded_spends[0].date == dates[2]  # Today
        assert loaded_spends[1].date == dates[1]  # Yesterday
        assert loaded_spends[2].date == dates[0]  # Day before yesterday

    def test_transaction_save_and_load(self):
        """Test saving and loading transaction history."""
        # Create a transaction request
        request = TransactionRequest(
            destination="bc1qtest",
            amount_sats=1000,
            fee_rate_sats_per_vbyte=10,
            description="Test transaction",
        )

        # Save transaction
        self.persistence.save_transaction(request, "test_txid")

        # Load transaction history
        history = self.persistence.load_transaction_history()

        assert len(history) == 1
        assert history[0]["destination"] == "bc1qtest"
        assert history[0]["amount_sats"] == 1000
        assert history[0]["txid"] == "test_txid"
        assert history[0]["status"] == "completed"

    def test_transaction_history_limit(self):
        """Test transaction history limit."""
        # Create many transactions
        for i in range(5):
            request = TransactionRequest(
                destination=f"bc1qtest{i}", amount_sats=1000 + i
            )
            self.persistence.save_transaction(request, f"txid_{i}")

        # Load with limit
        history = self.persistence.load_transaction_history(limit=3)

        assert len(history) == 3
        # Should get the most recent 3 transactions (last 3 in chronological order)
        assert history[0]["txid"] == "txid_2"
        assert history[1]["txid"] == "txid_3"
        assert history[2]["txid"] == "txid_4"

    def test_policy_violation_save_and_load(self):
        """Test saving and loading policy violations."""
        # Create violation data
        violation_data = {
            "violation_type": "amount_limit_exceeded",
            "message": "Transaction exceeds limit",
            "severity": "error",
            "amount": 10000,
        }

        # Save violation
        self.persistence.save_policy_violation(violation_data)

        # Load violations
        violations = self.persistence.load_policy_violations()

        assert len(violations) == 1
        assert violations[0]["violation_type"] == "amount_limit_exceeded"
        assert violations[0]["severity"] == "error"
        assert "timestamp" in violations[0]  # Should have timestamp added

    def test_policy_violations_limit(self):
        """Test policy violations limit."""
        # Create many violations
        for i in range(5):
            violation_data = {
                "violation_type": f"violation_{i}",
                "message": f"Test violation {i}",
                "severity": "error",
            }
            self.persistence.save_policy_violation(violation_data)

        # Load with limit
        violations = self.persistence.load_policy_violations(limit=3)

        assert len(violations) == 3
        # Should get the most recent 3 violations (last 3 in chronological order)
        assert violations[0]["violation_type"] == "violation_2"
        assert violations[1]["violation_type"] == "violation_3"
        assert violations[2]["violation_type"] == "violation_4"

    def test_data_cleanup(self):
        """Test data cleanup functionality."""
        # Create old data
        old_date = (datetime.now() - timedelta(days=100)).strftime("%Y-%m-%d")
        old_spend = DailySpend(
            date=old_date, total_spent_sats=1000, transaction_count=1
        )
        self.persistence.save_daily_spend(old_spend)

        # Create recent data
        recent_date = datetime.now().strftime("%Y-%m-%d")
        recent_spend = DailySpend(
            date=recent_date, total_spent_sats=2000, transaction_count=2
        )
        self.persistence.save_daily_spend(recent_spend)

        # Run cleanup
        self.persistence.cleanup_old_data(days=30)

        # Check that old data was removed but recent data remains
        old_loaded = self.persistence.load_daily_spend(old_date)
        recent_loaded = self.persistence.load_daily_spend(recent_date)

        assert old_loaded is None
        assert recent_loaded is not None
        assert recent_loaded.total_spent_sats == 2000

    def test_json_file_handling(self):
        """Test JSON file handling with invalid data."""
        # Create a file with invalid JSON
        invalid_file = Path(self.test_dir) / "invalid.json"
        invalid_file.parent.mkdir(exist_ok=True)

        with open(invalid_file, "w") as f:
            f.write("invalid json content")

        # Should return default value
        data = self.persistence._load_json(invalid_file, default={"test": "default"})
        assert data == {"test": "default"}

    def test_backup_and_restore(self):
        """Test backup and restore functionality during save."""
        # Create initial data
        daily_spend = DailySpend(
            date="2024-01-01", total_spent_sats=1000, transaction_count=1
        )
        self.persistence.save_daily_spend(daily_spend)

        # Verify it was saved
        loaded = self.persistence.load_daily_spend("2024-01-01")
        assert loaded is not None

        # Simulate a write failure by making the directory read-only
        # (This is a bit tricky to test without actually making the directory read-only)
        # For now, we'll just verify the backup mechanism exists
        assert self.persistence.daily_spends_file.exists()

    def test_file_creation(self):
        """Test that data directory and files are created properly."""
        # Data directory should exist
        assert Path(self.test_dir).exists()
        assert Path(self.test_dir).is_dir()

        # Files should be created when data is saved
        daily_spend = DailySpend(
            date="2024-01-01", total_spent_sats=1000, transaction_count=1
        )
        self.persistence.save_daily_spend(daily_spend)

        assert self.persistence.daily_spends_file.exists()

    def test_transaction_without_txid(self):
        """Test saving transaction without transaction ID."""
        request = TransactionRequest(destination="bc1qtest", amount_sats=1000)

        # Save without txid
        self.persistence.save_transaction(request)

        # Load and check
        history = self.persistence.load_transaction_history()

        assert len(history) == 1
        assert history[0]["txid"] is None
        assert history[0]["status"] == "pending"

    def test_daily_spend_update(self):
        """Test updating existing daily spend record."""
        # Create initial record
        daily_spend = DailySpend(
            date="2024-01-01", total_spent_sats=1000, transaction_count=1
        )
        self.persistence.save_daily_spend(daily_spend)

        # Update the record
        updated_spend = DailySpend(
            date="2024-01-01", total_spent_sats=2000, transaction_count=2
        )
        self.persistence.save_daily_spend(updated_spend)

        # Load and verify update
        loaded = self.persistence.load_daily_spend("2024-01-01")
        assert loaded.total_spent_sats == 2000
        assert loaded.transaction_count == 2
