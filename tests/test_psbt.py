"""Tests for Falconer PSBT functionality."""

from unittest.mock import Mock, patch

import pytest

from falconer.config import Config
from falconer.policy.schema import TransactionRequest
from falconer.wallet.psbt import PSBTInput, PSBTManager, PSBTOutput, PSBTTransaction


class TestPSBTManager:
    """Test cases for PSBTManager."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = Config(
            bitcoind_host="localhost",
            bitcoind_port=8332,
            bitcoind_rpc_user="test",
            bitcoind_rpc_password="test",
        )
        self.bitcoin_adapter = Mock()
        self.psbt_manager = PSBTManager(self.config, self.bitcoin_adapter)

    def test_estimate_fee_rate(self):
        """Test fee rate estimation."""
        # Mock successful fee estimation
        self.bitcoin_adapter.estimate_smart_fee.return_value = {"feerate": 0.00001}

        fee_rate = self.psbt_manager._estimate_fee_rate()
        assert fee_rate == 1.0  # 0.00001 BTC/kB = 1 sats/vbyte

        # Mock failed fee estimation
        self.bitcoin_adapter.estimate_smart_fee.side_effect = Exception("RPC error")

        fee_rate = self.psbt_manager._estimate_fee_rate()
        assert fee_rate == 10.0  # Default fallback

    def test_estimate_fee(self):
        """Test fee estimation."""
        inputs = [{"txid": "tx1", "vout": 0}, {"txid": "tx2", "vout": 1}]
        output_amount = 100000  # 100k sats
        fee_rate = 10.0  # 10 sats/vbyte

        estimated_fee = self.psbt_manager._estimate_fee(inputs, output_amount, fee_rate)

        # Expected size: 2 inputs * 148 + 2 outputs * 34 + 10 overhead = 374 bytes
        expected_size = 2 * 148 + 2 * 34 + 10
        expected_fee = expected_size * fee_rate

        assert estimated_fee == expected_fee

    def test_estimate_tx_size(self):
        """Test transaction size estimation."""
        size = self.psbt_manager._estimate_tx_size(2, 2)  # 2 inputs, 2 outputs

        # Expected: 2 * 148 + 2 * 34 + 10 = 374 bytes
        expected_size = 2 * 148 + 2 * 34 + 10
        assert size == expected_size

    def test_select_utxos_sufficient_funds(self):
        """Test UTXO selection with sufficient funds."""
        utxos = [
            {"txid": "tx1", "vout": 0, "amount": 0.001},  # 100k sats
            {"txid": "tx2", "vout": 1, "amount": 0.0005},  # 50k sats
            {"txid": "tx3", "vout": 2, "amount": 0.0001},  # 10k sats
        ]
        target_amount = 50000  # 50k sats

        selected = self.psbt_manager._select_utxos(utxos, target_amount)

        # Should select the largest UTXO first (100k sats)
        assert len(selected) == 1
        assert selected[0]["txid"] == "tx1"

    def test_select_utxos_insufficient_funds(self):
        """Test UTXO selection with insufficient funds."""
        utxos = [
            {"txid": "tx1", "vout": 0, "amount": 0.0001},  # 10k sats
        ]
        target_amount = 50000  # 50k sats

        with pytest.raises(Exception, match="Insufficient funds"):
            self.psbt_manager._select_utxos(utxos, target_amount)

    def test_select_utxos_multiple_utxos_needed(self):
        """Test UTXO selection requiring multiple UTXOs."""
        utxos = [
            {"txid": "tx1", "vout": 0, "amount": 0.0003},  # 30k sats
            {"txid": "tx2", "vout": 1, "amount": 0.0002},  # 20k sats
            {"txid": "tx3", "vout": 2, "amount": 0.0001},  # 10k sats
        ]
        target_amount = 40000  # 40k sats

        selected = self.psbt_manager._select_utxos(utxos, target_amount)

        # Should select the two largest UTXOs (30k + 20k = 50k sats)
        assert len(selected) == 2
        assert selected[0]["txid"] == "tx1"  # Largest first
        assert selected[1]["txid"] == "tx2"

    @patch("falconer.wallet.psbt.PSBTManager._get_change_address")
    def test_create_psbt_success(self, mock_get_change_address):
        """Test successful PSBT creation."""
        mock_get_change_address.return_value = "bc1qchange"

        # Mock Bitcoin Core responses
        self.bitcoin_adapter.list_unspent.return_value = [
            {"txid": "tx1", "vout": 0, "amount": 0.001, "scriptPubKey": "script1"}
        ]
        self.bitcoin_adapter._make_rpc_call.return_value = Mock(
            result={"psbt": "cHNidP8BAH0CAAAA..."}
        )

        request = TransactionRequest(
            destination="bc1qdestination", amount_sats=50000, fee_rate_sats_per_vbyte=10
        )

        psbt_tx = self.psbt_manager.create_psbt(request)

        assert isinstance(psbt_tx, PSBTTransaction)
        assert psbt_tx.psbt == "cHNidP8BAH0CAAAA..."
        assert len(psbt_tx.inputs) == 1
        assert len(psbt_tx.outputs) == 2  # destination + change
        assert psbt_tx.fee > 0
        assert psbt_tx.fee_rate == 10.0

    def test_create_psbt_no_utxos(self):
        """Test PSBT creation with no available UTXOs."""
        self.bitcoin_adapter.list_unspent.return_value = []

        request = TransactionRequest(destination="bc1qdestination", amount_sats=50000)

        with pytest.raises(Exception, match="No unspent outputs available"):
            self.psbt_manager.create_psbt(request)

    def test_finalize_psbt_success(self):
        """Test successful PSBT finalization."""
        self.bitcoin_adapter._make_rpc_call.return_value = Mock(
            result={"complete": True, "hex": "0200000001..."}
        )

        raw_tx = self.psbt_manager.finalize_psbt("cHNidP8BAH0CAAAA...")

        assert raw_tx == "0200000001..."

    def test_finalize_psbt_incomplete(self):
        """Test PSBT finalization with incomplete PSBT."""
        self.bitcoin_adapter._make_rpc_call.return_value = Mock(
            result={"complete": False, "hex": None}
        )

        with pytest.raises(Exception, match="PSBT is not complete"):
            self.psbt_manager.finalize_psbt("cHNidP8BAH0CAAAA...")

    def test_broadcast_psbt_success(self):
        """Test successful PSBT broadcasting."""
        # Mock finalization
        self.bitcoin_adapter._make_rpc_call.side_effect = [
            Mock(result={"complete": True, "hex": "0200000001..."}),  # finalizepsbt
            Mock(result="txid123"),  # sendrawtransaction
        ]

        txid = self.psbt_manager.broadcast_psbt("cHNidP8BAH0CAAAA...")

        assert txid == "txid123"

    def test_broadcast_psbt_finalization_fails(self):
        """Test PSBT broadcasting with finalization failure."""
        self.bitcoin_adapter._make_rpc_call.side_effect = Exception(
            "Finalization failed"
        )

        with pytest.raises(Exception, match="Finalization failed"):
            self.psbt_manager.broadcast_psbt("cHNidP8BAH0CAAAA...")


class TestPSBTModels:
    """Test cases for PSBT data models."""

    def test_psbt_input(self):
        """Test PSBTInput model."""
        input_data = PSBTInput(
            txid="tx123", vout=0, amount=100000, script_pubkey="script123"
        )

        assert input_data.txid == "tx123"
        assert input_data.vout == 0
        assert input_data.amount == 100000
        assert input_data.script_pubkey == "script123"

    def test_psbt_output(self):
        """Test PSBTOutput model."""
        output_data = PSBTOutput(address="bc1qtest", amount=50000)

        assert output_data.address == "bc1qtest"
        assert output_data.amount == 50000

    def test_psbt_transaction(self):
        """Test PSBTTransaction model."""
        inputs = [PSBTInput(txid="tx1", vout=0, amount=100000, script_pubkey="script1")]
        outputs = [
            PSBTOutput(address="bc1qdest", amount=50000),
            PSBTOutput(address="bc1qchange", amount=49000),
        ]

        psbt_tx = PSBTTransaction(
            psbt="cHNidP8BAH0CAAAA...",
            inputs=inputs,
            outputs=outputs,
            fee=1000,
            fee_rate=10.0,
            size=374,
            description="Test transaction",
        )

        assert psbt_tx.psbt == "cHNidP8BAH0CAAAA..."
        assert len(psbt_tx.inputs) == 1
        assert len(psbt_tx.outputs) == 2
        assert psbt_tx.fee == 1000
        assert psbt_tx.fee_rate == 10.0
        assert psbt_tx.size == 374
        assert psbt_tx.description == "Test transaction"
