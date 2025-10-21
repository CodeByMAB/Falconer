"""Persistence layer for Falconer data."""

import json
import os
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

from .logging import get_logger
from .policy.schema import DailySpend, TransactionRequest

logger = get_logger(__name__)


class PersistenceManager:
    """Manages persistent storage for Falconer data."""

    def __init__(self, data_dir: str = "data"):
        """Initialize persistence manager.

        Args:
            data_dir: Directory to store data files
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)

        self.daily_spends_file = self.data_dir / "daily_spends.json"
        self.transaction_history_file = self.data_dir / "transaction_history.json"
        self.policy_violations_file = self.data_dir / "policy_violations.json"

    def save_daily_spend(self, daily_spend: DailySpend) -> None:
        """Save daily spend record.

        Args:
            daily_spend: Daily spend record to save
        """
        try:
            # Load existing data
            daily_spends = self._load_daily_spends()

            # Update or add the record
            daily_spends[daily_spend.date] = daily_spend.model_dump()

            # Save back to file
            self._save_json(self.daily_spends_file, daily_spends)

            logger.info(
                "Daily spend saved",
                date=daily_spend.date,
                amount=daily_spend.total_spent_sats,
            )

        except Exception as e:
            logger.error(
                "Failed to save daily spend", error=str(e), date=daily_spend.date
            )
            raise

    def load_daily_spend(self, date_str: str) -> Optional[DailySpend]:
        """Load daily spend record for a specific date.

        Args:
            date_str: Date in YYYY-MM-DD format

        Returns:
            Daily spend record or None if not found
        """
        try:
            daily_spends = self._load_daily_spends()
            if date_str in daily_spends:
                return DailySpend(**daily_spends[date_str])
            return None

        except Exception as e:
            logger.error("Failed to load daily spend", error=str(e), date=date_str)
            return None

    def load_daily_spends(self, days: int = 30) -> List[DailySpend]:
        """Load daily spend records for the last N days.

        Args:
            days: Number of days to load

        Returns:
            List of daily spend records
        """
        try:
            daily_spends = self._load_daily_spends()
            cutoff_date = datetime.now().date()

            result = []
            for i in range(days):
                check_date = cutoff_date - timedelta(days=i)
                date_str = check_date.strftime("%Y-%m-%d")

                if date_str in daily_spends:
                    result.append(DailySpend(**daily_spends[date_str]))

            return result

        except Exception as e:
            logger.error("Failed to load daily spends", error=str(e))
            return []

    def save_transaction(
        self, request: TransactionRequest, txid: Optional[str] = None
    ) -> None:
        """Save transaction to history.

        Args:
            request: Transaction request
            txid: Transaction ID if available
        """
        try:
            # Load existing history
            history = self._load_json(self.transaction_history_file, [])

            # Ensure history is a list
            if not isinstance(history, list):
                history = []

            # Create transaction record
            transaction_record = {
                "timestamp": request.created_at.isoformat(),
                "destination": request.destination,
                "amount_sats": request.amount_sats,
                "fee_rate_sats_per_vbyte": request.fee_rate_sats_per_vbyte,
                "description": request.description,
                "txid": txid,
                "status": "completed" if txid else "pending",
            }

            # Add to history
            history.append(transaction_record)

            # Keep only last 1000 transactions
            if len(history) > 1000:
                history = history[-1000:]

            # Save back to file
            self._save_json(self.transaction_history_file, history)

            logger.info(
                "Transaction saved to history", txid=txid, amount=request.amount_sats
            )

        except Exception as e:
            logger.error("Failed to save transaction", error=str(e))
            raise

    def load_transaction_history(self, limit: int = 100) -> List[Dict]:
        """Load transaction history.

        Args:
            limit: Maximum number of transactions to return

        Returns:
            List of transaction records
        """
        try:
            history = self._load_json(self.transaction_history_file, [])
            return history[-limit:] if limit else history

        except Exception as e:
            logger.error("Failed to load transaction history", error=str(e))
            return []

    def save_policy_violation(self, violation_data: Dict) -> None:
        """Save policy violation record.

        Args:
            violation_data: Policy violation data
        """
        try:
            # Load existing violations
            violations = self._load_json(self.policy_violations_file, [])

            # Ensure violations is a list
            if not isinstance(violations, list):
                violations = []

            # Add timestamp
            violation_data["timestamp"] = datetime.utcnow().isoformat()

            # Add to violations
            violations.append(violation_data)

            # Keep only last 500 violations
            if len(violations) > 500:
                violations = violations[-500:]

            # Save back to file
            self._save_json(self.policy_violations_file, violations)

            logger.warning(
                "Policy violation recorded",
                violation_type=violation_data.get("violation_type"),
                severity=violation_data.get("severity"),
            )

        except Exception as e:
            logger.error("Failed to save policy violation", error=str(e))
            raise

    def load_policy_violations(self, limit: int = 100) -> List[Dict]:
        """Load policy violation history.

        Args:
            limit: Maximum number of violations to return

        Returns:
            List of policy violation records
        """
        try:
            violations = self._load_json(self.policy_violations_file, [])
            return violations[-limit:] if limit else violations

        except Exception as e:
            logger.error("Failed to load policy violations", error=str(e))
            return []

    def _load_daily_spends(self) -> Dict[str, Dict]:
        """Load daily spends from file.

        Returns:
            Dictionary of daily spend records
        """
        return self._load_json(self.daily_spends_file, {})

    def _load_json(self, file_path: Path, default: any = None) -> any:
        """Load JSON data from file.

        Args:
            file_path: Path to JSON file
            default: Default value if file doesn't exist

        Returns:
            Loaded JSON data or default value
        """
        if not file_path.exists():
            return default or {}

        try:
            with open(file_path, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(
                "Failed to load JSON file, using default",
                file=str(file_path),
                error=str(e),
            )
            return default or {}

    def _save_json(self, file_path: Path, data: any) -> None:
        """Save JSON data to file.

        Args:
            file_path: Path to JSON file
            data: Data to save
        """
        try:
            # Create backup if file exists
            if file_path.exists():
                backup_path = file_path.with_suffix(".json.bak")
                file_path.rename(backup_path)

            # Write new data
            def json_serializer(obj):
                if isinstance(obj, datetime):
                    return obj.isoformat()
                raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

            with open(file_path, "w") as f:
                json.dump(data, f, indent=2, default=json_serializer)

            # Remove backup if write was successful
            backup_path = file_path.with_suffix(".json.bak")
            if backup_path.exists():
                backup_path.unlink()

        except Exception as e:
            # Restore backup if write failed
            backup_path = file_path.with_suffix(".json.bak")
            if backup_path.exists():
                backup_path.rename(file_path)
            raise

    def cleanup_old_data(self, days: int = 90) -> None:
        """Clean up old data files.

        Args:
            days: Number of days to keep data
        """
        try:
            cutoff_date = datetime.now().date() - timedelta(days=days)

            # Clean up old daily spends
            daily_spends = self._load_daily_spends()
            cleaned_spends = {
                date_str: data
                for date_str, data in daily_spends.items()
                if datetime.strptime(date_str, "%Y-%m-%d").date() >= cutoff_date
            }
            self._save_json(self.daily_spends_file, cleaned_spends)

            logger.info("Old data cleaned up", cutoff_date=cutoff_date.isoformat())

        except Exception as e:
            logger.error("Failed to cleanup old data", error=str(e))
