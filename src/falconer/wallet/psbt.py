"""PSBT (Partially Signed Bitcoin Transaction) management for Falconer."""

import json
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from ..adapters.bitcoind import BitcoinAdapter
from ..config import Config
from ..exceptions import InsufficientFundsError, PSBTError
from ..logging import get_logger
from ..policy.schema import TransactionRequest

# Bitcoin transaction size constants
INPUT_SIZE_BYTES = 148  # Approximate size of a P2WPKH input
OUTPUT_SIZE_BYTES = 34  # Approximate size of a P2WPKH output
TX_OVERHEAD_BYTES = 10  # Transaction overhead (version, locktime, etc.)
DUST_THRESHOLD_SATS = 546  # Bitcoin dust threshold

logger = get_logger(__name__)


class PSBTInput(BaseModel):
    """PSBT input model."""

    txid: str = Field(description="Previous transaction ID")
    vout: int = Field(description="Output index")
    amount: int = Field(description="Amount in satoshis")
    script_pubkey: str = Field(description="Script public key")


class PSBTOutput(BaseModel):
    """PSBT output model."""

    address: str = Field(description="Output address")
    amount: int = Field(description="Amount in satoshis")


class PSBTTransaction(BaseModel):
    """PSBT transaction model."""

    psbt: str = Field(description="PSBT hex string")
    inputs: List[PSBTInput] = Field(description="Transaction inputs")
    outputs: List[PSBTOutput] = Field(description="Transaction outputs")
    fee: int = Field(description="Transaction fee in satoshis")
    fee_rate: float = Field(description="Fee rate in sats/vbyte")
    size: int = Field(description="Transaction size in bytes")
    description: Optional[str] = Field(None, description="Transaction description")


class PSBTManager:
    """Manager for PSBT creation and handling."""

    def __init__(self, config: Config, bitcoin_adapter: BitcoinAdapter):
        """Initialize PSBT manager.

        Args:
            config: Falconer configuration
            bitcoin_adapter: Bitcoin Core adapter
        """
        self.config = config
        self.bitcoin_adapter = bitcoin_adapter

    def create_psbt(self, request: TransactionRequest) -> PSBTTransaction:
        """Create a PSBT for a transaction request.

        Args:
            request: Transaction request

        Returns:
            PSBT transaction

        Raises:
            Exception: If PSBT creation fails
        """
        try:
            # Get available UTXOs
            utxos = self.bitcoin_adapter.list_unspent()
            if not utxos:
                raise Exception("No unspent outputs available")

            # Select UTXOs for the transaction
            selected_utxos = self._select_utxos(utxos, request.amount_sats)

            # Calculate fee
            fee_rate = request.fee_rate_sats_per_vbyte or self._estimate_fee_rate()
            estimated_fee = self._estimate_fee(
                selected_utxos, request.amount_sats, fee_rate
            )

            # Create transaction inputs
            inputs = []
            total_input = 0
            for utxo in selected_utxos:
                inputs.append({"txid": utxo["txid"], "vout": utxo["vout"]})
                total_input += int(utxo["amount"] * 100000000)  # Convert BTC to sats

            # Create transaction outputs
            outputs = {
                request.destination: request.amount_sats
                / 100000000  # Convert sats to BTC
            }

            # Add change output if needed
            change_amount = total_input - request.amount_sats - estimated_fee
            if change_amount > DUST_THRESHOLD_SATS:
                # Get a change address (simplified - in practice you'd use proper address generation)
                change_address = self._get_change_address()
                outputs[change_address] = change_amount / 100000000

            # Create raw transaction
            raw_tx = self.bitcoin_adapter.create_raw_transaction(inputs, outputs)

            # Create PSBT
            psbt_result = self.bitcoin_adapter._make_rpc_call(
                "walletcreatefundedpsbt",
                [inputs, outputs, 0, {"feeRate": fee_rate}],  # locktime
            )

            psbt_hex = psbt_result.result["psbt"]

            # Create PSBT transaction model
            psbt_inputs = [
                PSBTInput(
                    txid=utxo["txid"],
                    vout=utxo["vout"],
                    amount=int(utxo["amount"] * 100000000),
                    script_pubkey=utxo["scriptPubKey"],
                )
                for utxo in selected_utxos
            ]

            psbt_outputs = [
                PSBTOutput(address=request.destination, amount=request.amount_sats)
            ]

            if change_amount > DUST_THRESHOLD_SATS:
                psbt_outputs.append(
                    PSBTOutput(address=change_address, amount=change_amount)
                )

            # Estimate transaction size
            tx_size = self._estimate_tx_size(len(psbt_inputs), len(psbt_outputs))

            return PSBTTransaction(
                psbt=psbt_hex,
                inputs=psbt_inputs,
                outputs=psbt_outputs,
                fee=estimated_fee,
                fee_rate=fee_rate,
                size=tx_size,
                description=request.description,
            )

        except Exception as e:
            logger.error("Failed to create PSBT", error=str(e), request=request.dict())
            raise PSBTError(f"Failed to create PSBT: {e}")

    def finalize_psbt(self, psbt_hex: str) -> str:
        """Finalize a PSBT to get the raw transaction.

        Args:
            psbt_hex: PSBT hex string

        Returns:
            Raw transaction hex string
        """
        try:
            result = self.bitcoin_adapter._make_rpc_call("finalizepsbt", [psbt_hex])
            if not result.result["complete"]:
                raise Exception("PSBT is not complete")
            return result.result["hex"]
        except Exception as e:
            logger.error("Failed to finalize PSBT", error=str(e))
            raise PSBTError(f"Failed to finalize PSBT: {e}")

    def broadcast_psbt(self, psbt_hex: str) -> str:
        """Broadcast a finalized PSBT.

        Args:
            psbt_hex: PSBT hex string

        Returns:
            Transaction ID
        """
        try:
            # First finalize the PSBT
            raw_tx = self.finalize_psbt(psbt_hex)

            # Then broadcast the raw transaction
            txid = self.bitcoin_adapter.send_raw_transaction(raw_tx)
            logger.info("PSBT broadcast successfully", txid=txid)
            return txid
        except Exception as e:
            logger.error("Failed to broadcast PSBT", error=str(e))
            raise PSBTError(f"Failed to broadcast PSBT: {e}")

    def _select_utxos(
        self, utxos: List[Dict[str, Any]], target_amount: int
    ) -> List[Dict[str, Any]]:
        """Select UTXOs for a transaction using a simple selection algorithm.

        Args:
            utxos: Available UTXOs
            target_amount: Target amount in satoshis

        Returns:
            Selected UTXOs
        """
        # Sort UTXOs by amount (largest first)
        sorted_utxos = sorted(utxos, key=lambda x: x["amount"], reverse=True)

        selected = []
        total = 0

        for utxo in sorted_utxos:
            selected.append(utxo)
            total += int(utxo["amount"] * 100000000)  # Convert BTC to sats

            # Add some buffer for fees (rough estimate)
            if total >= target_amount + 10000:  # 10k sats buffer
                break

        if total < target_amount:
            raise InsufficientFundsError(
                f"Insufficient funds: need {target_amount} sats, have {total} sats"
            )

        return selected

    def _estimate_fee_rate(self) -> float:
        """Estimate current fee rate.

        Returns:
            Fee rate in sats/vbyte
        """
        try:
            fee_estimate = self.bitcoin_adapter.estimate_smart_fee(6)
            if "feerate" in fee_estimate:
                return fee_estimate["feerate"] * 100000  # Convert BTC/kB to sats/vbyte
            else:
                return 10.0  # Default fallback
        except Exception:
            return 10.0  # Default fallback

    def _estimate_fee(
        self, inputs: List[Dict[str, Any]], output_amount: int, fee_rate: float
    ) -> int:
        """Estimate transaction fee.

        Args:
            inputs: Transaction inputs
            output_amount: Output amount in satoshis
            fee_rate: Fee rate in sats/vbyte

        Returns:
            Estimated fee in satoshis
        """
        # Rough estimation using constants
        estimated_size = (
            len(inputs) * INPUT_SIZE_BYTES + 2 * OUTPUT_SIZE_BYTES + TX_OVERHEAD_BYTES
        )  # Assuming 2 outputs (destination + change)
        return int(estimated_size * fee_rate)

    def _estimate_tx_size(self, input_count: int, output_count: int) -> int:
        """Estimate transaction size.

        Args:
            input_count: Number of inputs
            output_count: Number of outputs

        Returns:
            Estimated size in bytes
        """
        return (
            input_count * INPUT_SIZE_BYTES
            + output_count * OUTPUT_SIZE_BYTES
            + TX_OVERHEAD_BYTES
        )

    def _get_change_address(self) -> str:
        """Get a change address.

        Returns:
            Change address

        Raises:
            Exception: If change address generation fails
        """
        try:
            # Get a new address from the wallet
            response = self.bitcoin_adapter._make_rpc_call(
                "getnewaddress", ["", "bech32"]
            )
            return response.result
        except Exception as e:
            # Fallback to a configurable change address or raise error
            if hasattr(self.config, "change_address") and self.config.change_address:
                return self.config.change_address
            raise PSBTError(f"Failed to generate change address: {e}")
