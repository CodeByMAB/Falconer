"""Command-line interface for Falconer."""

import json
from pathlib import Path
from typing import Optional

import click
from dotenv import load_dotenv

from .adapters.bitcoind import BitcoinAdapter
from .adapters.electrs import ElectrsAdapter
from .adapters.lnbits import LNbitsAdapter
from .config import Config
from .exceptions import (
    AddressValidationError,
    BitcoinRPCError,
    FalconerError,
    InsufficientFundsError,
    PolicyViolationError,
    PSBTError,
)
from .logging import get_logger, setup_logging
from .policy.engine import PolicyEngine
from .policy.schema import Policy
from .tasks.fee_brief import FeeBriefTask
from .validation import validate_bitcoin_address
from .wallet.psbt import PSBTManager

# Load environment variables
load_dotenv()

logger = get_logger(__name__)


@click.group()
@click.option("--config", "-c", help="Configuration file path")
@click.option("--log-level", default="INFO", help="Log level")
@click.pass_context
def main(ctx, config: Optional[str], log_level: str):
    """Falconer - A Bitcoin-native AI agent built to hunt for insights and earn sats."""
    # Setup logging
    setup_logging(log_level=log_level)

    # Load configuration
    if config:
        config_path = Path(config)
        if config_path.exists():
            load_dotenv(config_path)

    ctx.ensure_object(dict)
    ctx.obj["config"] = Config()


@main.command()
@click.option("--output", "-o", help="Output file path")
@click.pass_context
def fee_brief(ctx, output: Optional[str]):
    """Generate a fee intelligence brief."""
    config = ctx.obj["config"]

    try:
        # Initialize adapters
        bitcoin_adapter = BitcoinAdapter(config)
        electrs_adapter = ElectrsAdapter(config)

        # Create fee brief task
        fee_task = FeeBriefTask(config, bitcoin_adapter, electrs_adapter)

        # Generate brief
        brief = fee_task.generate_fee_brief()

        # Output results
        if output:
            fee_task.save_fee_brief(brief, output)
            click.echo(f"Fee brief saved to {output}")
        else:
            click.echo(json.dumps(brief.dict(), indent=2, default=str))

        # Cleanup
        bitcoin_adapter.close()
        electrs_adapter.close()

    except Exception as e:
        logger.error("Failed to generate fee brief", error=str(e))
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()


@main.command()
@click.option("--address", required=True, help="Destination address")
@click.option("--amount", required=True, type=int, help="Amount in satoshis")
@click.option("--fee-rate", type=float, help="Fee rate in sats/vbyte")
@click.option("--description", help="Transaction description")
@click.option("--dry-run", is_flag=True, help="Create PSBT without broadcasting")
@click.pass_context
def send(
    ctx,
    address: str,
    amount: int,
    fee_rate: Optional[float],
    description: Optional[str],
    dry_run: bool,
):
    """Create and optionally broadcast a Bitcoin transaction."""
    config = ctx.obj["config"]

    try:
        # Initialize adapters
        bitcoin_adapter = BitcoinAdapter(config)

        # Create policy engine
        policy = Policy(
            max_daily_spend_sats=config.max_daily_spend_sats,
            max_single_tx_sats=config.max_single_tx_sats,
            allowed_destinations=config.allowed_destinations,
        )
        policy_engine = PolicyEngine(policy)

        # Create PSBT manager
        psbt_manager = PSBTManager(config, bitcoin_adapter)

        # Validate Bitcoin address
        try:
            validate_bitcoin_address(address)
        except AddressValidationError as e:
            click.echo(f"Invalid Bitcoin address: {e}", err=True)
            raise click.Abort()

        # Create transaction request
        from .policy.schema import TransactionRequest

        request = TransactionRequest(
            destination=address,
            amount_sats=amount,
            fee_rate_sats_per_vbyte=fee_rate,
            description=description,
        )

        # Validate transaction against policy
        violations = policy_engine.validate_transaction(request)
        if violations:
            click.echo("Policy violations detected:", err=True)
            for violation in violations:
                click.echo(
                    f"  - {violation.violation_type}: {violation.message}", err=True
                )
            raise click.Abort()

        # Create PSBT
        psbt_tx = psbt_manager.create_psbt(request)

        click.echo(f"PSBT created successfully:")
        click.echo(f"  Fee: {psbt_tx.fee} sats")
        click.echo(f"  Fee rate: {psbt_tx.fee_rate:.2f} sats/vbyte")
        click.echo(f"  Size: {psbt_tx.size} bytes")
        click.echo(f"  PSBT: {psbt_tx.psbt}")

        if not dry_run:
            # Broadcast transaction
            txid = psbt_manager.broadcast_psbt(psbt_tx.psbt)
            click.echo(f"Transaction broadcast: {txid}")

            # Record transaction in policy engine
            policy_engine.record_transaction(request, txid)

        # Cleanup
        bitcoin_adapter.close()

    except (
        BitcoinRPCError,
        PSBTError,
        InsufficientFundsError,
        PolicyViolationError,
    ) as e:
        logger.error("Transaction failed", error=str(e))
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()
    except Exception as e:
        logger.error("Unexpected error during transaction", error=str(e))
        click.echo(f"Unexpected error: {e}", err=True)
        raise click.Abort()


@main.command()
@click.pass_context
def balance(ctx):
    """Get wallet balance information."""
    config = ctx.obj["config"]

    try:
        # Initialize adapters
        bitcoin_adapter = BitcoinAdapter(config)
        lnbits_adapter = LNbitsAdapter(config)

        # Get Bitcoin balance
        btc_balance = bitcoin_adapter.get_balance()
        click.echo(f"Bitcoin balance: {btc_balance:.8f} BTC")

        # Get Lightning balance
        ln_balance = lnbits_adapter.get_wallet_balance()
        click.echo(f"Lightning balance: {ln_balance.get('balance', 0)} sats")

        # Cleanup
        bitcoin_adapter.close()
        lnbits_adapter.close()

    except Exception as e:
        logger.error("Failed to get balance", error=str(e))
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()


@main.command()
@click.pass_context
def status(ctx):
    """Get system status and connectivity."""
    config = ctx.obj["config"]

    try:
        # Initialize adapters
        bitcoin_adapter = BitcoinAdapter(config)
        electrs_adapter = ElectrsAdapter(config)
        lnbits_adapter = LNbitsAdapter(config)

        # Check Bitcoin Knots
        try:
            blockchain_info = bitcoin_adapter.get_blockchain_info()
            click.echo(
                f"✓ Bitcoin Knots: {blockchain_info['blocks']} blocks, {blockchain_info['chain']} chain"
            )
        except Exception as e:
            click.echo(f"✗ Bitcoin Knots: {e}", err=True)

        # Check Electrs
        try:
            tip_height = electrs_adapter.get_tip_height()
            click.echo(f"✓ Electrs: {tip_height} blocks")
        except Exception as e:
            click.echo(f"✗ Electrs: {e}", err=True)

        # Check LNbits
        try:
            ln_balance = lnbits_adapter.get_wallet_balance()
            click.echo(f"✓ LNbits: {ln_balance.get('balance', 0)} sats")
        except Exception as e:
            click.echo(f"✗ LNbits: {e}", err=True)

        # Cleanup
        bitcoin_adapter.close()
        electrs_adapter.close()
        lnbits_adapter.close()

    except Exception as e:
        logger.error("Failed to get status", error=str(e))
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()


@main.command()
@click.pass_context
def mempool_health(ctx):
    """Check Mempool reachability and tip height without touching Core RPC."""
    from asyncio import run as asyncio_run

    from .adapters.mempool import MempoolAdapter

    try:

        async def _run():
            adapter = MempoolAdapter()
            tip = await adapter.tip_height()
            click.echo("Mempool Health")
            click.echo("================")
            click.echo(f"Mode: {adapter.mode}")
            click.echo(f"Tip height: {tip}")

        asyncio_run(_run())
    except Exception as e:
        logger.error("Failed to get mempool health", error=str(e))
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()


if __name__ == "__main__":
    main()
