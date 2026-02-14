"""Command-line interface for Falconer."""

import json
from pathlib import Path
from typing import Optional

import click
from dotenv import load_dotenv

from .adapters.bitcoind import BitcoinAdapter
from .adapters.electrs import ElectrsAdapter
from .adapters.lnbits import LNbitsAdapter
from .ai.agent import AIAgent
from .ai.market_analyzer import MarketAnalyzer
from .ai.earning_strategies import EarningStrategyManager
from .config import Config
from .persistence import PersistenceManager
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

# Import funding modules here to avoid circular imports
try:
    from .funding.manager import FundingProposalManager
    from .funding.n8n_adapter import N8nAdapter
    from .funding.webhook_server import create_webhook_app, run_webhook_server
except ImportError:
    # Handle case where funding module is not available
    FundingProposalManager = None
    N8nAdapter = None
    create_webhook_app = None
    run_webhook_server = None

# Import API module for OpenClaw integration
try:
    from .api.test_endpoints import run_api_server
except ImportError:
    run_api_server = None

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


@main.command()
@click.option("--model", default="llama3.1:8b", help="vLLM model to use")
@click.option(
    "--base-url",
    default="http://localhost:8000/v1",
    help="vLLM OpenAI-compatible API base URL",
)
@click.pass_context
def ai_start(ctx, model: str, base_url: str):
    """Start the AI agent in autonomous earning mode."""
    from asyncio import run as asyncio_run

    config = ctx.obj["config"]

    # Set vLLM configuration
    config.vllm_model = model
    config.vllm_base_url = base_url.rstrip("/")
    if not config.vllm_base_url.endswith("/v1"):
        config.vllm_base_url = config.vllm_base_url + "/v1"

    try:
        async def _run():
            # Initialize AI agent
            ai_agent = AIAgent(config)

            click.echo("🤖 Starting Falconer AI Agent")
            click.echo(f"Model: {model}")
            click.echo(f"Base URL: {config.vllm_base_url}")
            click.echo("Press Ctrl+C to stop...")
            
            # Start autonomous mode
            await ai_agent.start_autonomous_mode()
        
        asyncio_run(_run())
        
    except KeyboardInterrupt:
        click.echo("\n🛑 AI Agent stopped by user")
    except Exception as e:
        logger.error("Failed to start AI agent", error=str(e))
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()


@main.command()
@click.pass_context
def ai_status(ctx):
    """Get status of the AI agent."""
    from asyncio import run as asyncio_run
    
    config = ctx.obj["config"]
    
    try:
        async def _run():
            ai_agent = AIAgent(config)
            status = await ai_agent.get_agent_status()
            
            click.echo("🤖 Falconer AI Agent Status")
            click.echo("==========================")
            click.echo(f"Active: {status['is_active']}")
            click.echo(f"Model: {status['model']}")
            click.echo(f"Host: {status['host']}")
            click.echo(f"Current Balance: {status['state']['current_balance_sats']} sats")
            click.echo(f"Daily Earnings: {status['state']['daily_earnings_sats']} sats")
            click.echo(f"Risk Level: {status['state']['risk_level']}")
            click.echo(f"Confidence Score: {status['state']['confidence_score']:.2f}")
            click.echo(f"Recent Decisions: {status['recent_decisions_count']}")
            click.echo(f"Last Decision: {status['last_decision_time']}")
        
        asyncio_run(_run())
        
    except Exception as e:
        logger.error("Failed to get AI status", error=str(e))
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()


@main.command()
@click.pass_context
def ai_analyze(ctx):
    """Perform AI-powered market analysis."""
    from asyncio import run as asyncio_run
    
    config = ctx.obj["config"]
    
    try:
        async def _run():
            market_analyzer = MarketAnalyzer(config)
            
            click.echo("🔍 Performing AI Market Analysis...")
            
            # Analyze current conditions
            condition = await market_analyzer.analyze_current_conditions()
            
            click.echo("\n📊 Market Analysis Results")
            click.echo("=========================")
            click.echo(f"Timestamp: {condition.timestamp}")
            click.echo(f"Fee Trend: {condition.fee_trend}")
            click.echo(f"Mempool Congestion: {condition.mempool_congestion}")
            click.echo(f"Network Activity: {condition.network_activity}")
            click.echo(f"Opportunity Score: {condition.opportunity_score:.2f}")
            click.echo(f"Confidence: {condition.confidence:.2f}")
            
            click.echo("\n💡 Recommended Actions:")
            for i, action in enumerate(condition.recommended_actions, 1):
                click.echo(f"  {i}. {action}")
            
            # Identify earning opportunities
            opportunities = await market_analyzer.identify_earning_opportunities()
            
            if opportunities:
                click.echo(f"\n💰 Earning Opportunities ({len(opportunities)}):")
                for i, opp in enumerate(opportunities, 1):
                    click.echo(f"  {i}. {opp.opportunity_type}")
                    click.echo(f"     Description: {opp.description}")
                    click.echo(f"     Potential Earnings: {opp.potential_earnings_sats} sats")
                    click.echo(f"     Risk Level: {opp.risk_level}")
                    click.echo(f"     Confidence: {opp.confidence:.2f}")
                    click.echo()
            
            market_analyzer.close()
        
        asyncio_run(_run())
        
    except Exception as e:
        logger.error("Failed to perform AI analysis", error=str(e))
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()


@main.command()
@click.pass_context
def ai_strategies(ctx):
    """List available AI earning strategies."""
    from asyncio import run as asyncio_run
    
    config = ctx.obj["config"]
    
    try:
        async def _run():
            strategy_manager = EarningStrategyManager(config)
            
            click.echo("🎯 Available AI Earning Strategies")
            click.echo("==================================")
            
            strategies = strategy_manager.get_available_strategies()
            
            for strategy in strategies:
                click.echo(f"\n📋 {strategy['name'].replace('_', ' ').title()}")
                click.echo(f"   Description: {strategy['description']}")
                click.echo(f"   Current Price: {strategy['current_price_sats']} sats")
                click.echo(f"   Price Range: {strategy['min_price_sats']}-{strategy['max_price_sats']} sats")
                click.echo(f"   Risk Level: {strategy['risk_level']}")
                click.echo(f"   Time to Complete: {strategy['time_to_complete_minutes']} minutes")
                click.echo(f"   Success Rate: {strategy['success_rate']:.2f}")
                click.echo(f"   Total Earnings: {strategy['total_earnings']} sats")
                click.echo(f"   Total Uses: {strategy['total_uses']}")
            
            strategy_manager.close()
        
        asyncio_run(_run())
        
    except Exception as e:
        logger.error("Failed to list strategies", error=str(e))
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()


@main.command()
@click.option("--strategy", required=True, help="Strategy to execute")
@click.option("--dry-run", is_flag=True, help="Simulate execution without creating services")
@click.pass_context
def ai_execute(ctx, strategy: str, dry_run: bool):
    """Execute a specific AI earning strategy."""
    from asyncio import run as asyncio_run
    
    config = ctx.obj["config"]
    
    try:
        async def _run():
            strategy_manager = EarningStrategyManager(config)
            
            click.echo(f"🚀 Executing Strategy: {strategy}")
            if dry_run:
                click.echo("🔍 DRY RUN MODE - No actual services will be created")
            
            # Execute strategy
            execution = await strategy_manager.execute_strategy(strategy, {"dry_run": dry_run})
            
            click.echo("\n📊 Execution Results")
            click.echo("===================")
            click.echo(f"Strategy: {execution.strategy_name}")
            click.echo(f"Success: {execution.success}")
            click.echo(f"Price Charged: {execution.price_charged_sats} sats")
            click.echo(f"Earnings: {execution.earnings_sats} sats")
            click.echo(f"Execution Time: {execution.execution_time_seconds:.2f} seconds")
            
            if execution.error_message:
                click.echo(f"Error: {execution.error_message}")
            
            strategy_manager.close()
        
        asyncio_run(_run())
        
    except Exception as e:
        logger.error("Failed to execute strategy", error=str(e))
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()


@main.group()
def proposals():
    """Manage funding proposals."""
    pass


@proposals.command("list")
@click.option("--status", help="Filter by status (pending, approved, rejected, executed, expired)")
@click.option("--limit", default=20, help="Maximum number of proposals to show")
@click.pass_context
def proposals_list(ctx, status: Optional[str], limit: int):
    """List funding proposals."""
    try:
        config = ctx.obj["config"]
        persistence = PersistenceManager()
        
        if not FundingProposalManager:
            click.echo("Funding proposal module not available", err=True)
            return
        
        proposal_manager = FundingProposalManager(config, persistence, LNbitsAdapter(config))
        proposals = proposal_manager.list_proposals(status=status, limit=limit)
        
        if not proposals:
            click.echo("No proposals found")
            return
        
        # Display proposals in table format
        click.echo(f"{'ID':<12} {'Created':<20} {'Status':<12} {'Amount (sats)':<15} {'Justification'}")
        click.echo("-" * 80)
        
        for proposal in proposals:
            created_str = proposal.created_at.strftime("%Y-%m-%d %H:%M")
            click.echo(
                f"{proposal.proposal_id[:8]:<12} "
                f"{created_str:<20} "
                f"{proposal.status:<12} "
                f"{proposal.requested_amount_sats:<15,} "
                f"{proposal.justification[:50]}..."
            )
            
    except Exception as e:
        logger.error("Failed to list proposals", error=str(e))
        click.echo(f"Error: {e}", err=True)


@proposals.command("show")
@click.argument("proposal_id")
@click.pass_context
def proposals_show(ctx, proposal_id: str):
    """Show detailed information for a specific proposal."""
    try:
        config = ctx.obj["config"]
        persistence = PersistenceManager()
        
        if not FundingProposalManager:
            click.echo("Funding proposal module not available", err=True)
            return
        
        proposal_manager = FundingProposalManager(config, persistence, LNbitsAdapter(config))
        proposal = proposal_manager.get_proposal(proposal_id)
        
        if not proposal:
            click.echo(f"Proposal {proposal_id} not found", err=True)
            return
        
        # Display proposal details
        click.echo(f"Proposal ID: {proposal.proposal_id}")
        click.echo(f"Created: {proposal.created_at}")
        click.echo(f"Status: {proposal.status}")
        click.echo(f"Requested Amount: {proposal.requested_amount_sats:,} sats")
        click.echo(f"Current Balance: {proposal.current_balance_sats:,} sats")
        click.echo(f"Expected ROI: {proposal.expected_roi_sats:,} sats")
        click.echo(f"Risk Assessment: {proposal.risk_assessment}")
        click.echo(f"Time Horizon: {proposal.time_horizon_days} days")
        click.echo(f"Strategies: {', '.join(proposal.strategies_to_execute)}")
        click.echo(f"\nJustification:\n{proposal.justification}")
        click.echo(f"\nIntended Use:\n{proposal.intended_use}")
        
        if proposal.approved_at:
            click.echo(f"\nApproved: {proposal.approved_at} by {proposal.approved_by}")
        
        if proposal.executed_at:
            click.echo(f"Executed: {proposal.executed_at}")
            click.echo(f"Transaction ID: {proposal.execution_txid}")
        
        if proposal.n8n_workflow_id:
            click.echo(f"n8n Workflow ID: {proposal.n8n_workflow_id}")
            
    except Exception as e:
        logger.error("Failed to show proposal", error=str(e))
        click.echo(f"Error: {e}", err=True)


@proposals.command("approve")
@click.argument("proposal_id")
@click.option("--notes", help="Approval notes")
@click.pass_context
def proposals_approve(ctx, proposal_id: str, notes: Optional[str]):
    """Manually approve a proposal (for testing or manual workflow)."""
    try:
        config = ctx.obj["config"]
        persistence = PersistenceManager()
        
        if not FundingProposalManager:
            click.echo("Funding proposal module not available", err=True)
            return
        
        proposal_manager = FundingProposalManager(config, persistence, LNbitsAdapter(config))
        proposal = proposal_manager.approve_proposal(proposal_id, "manual_cli", notes)
        
        click.echo(f"Proposal {proposal_id} approved successfully")
        click.echo(f"Status: {proposal.status}")
        click.echo("Note: In production, approvals come via n8n webhook")
        
    except Exception as e:
        logger.error("Failed to approve proposal", error=str(e))
        click.echo(f"Error: {e}", err=True)


@proposals.command("reject")
@click.argument("proposal_id")
@click.option("--reason", required=True, help="Rejection reason")
@click.pass_context
def proposals_reject(ctx, proposal_id: str, reason: str):
    """Manually reject a proposal."""
    try:
        config = ctx.obj["config"]
        persistence = PersistenceManager()
        
        if not FundingProposalManager:
            click.echo("Funding proposal module not available", err=True)
            return
        
        proposal_manager = FundingProposalManager(config, persistence, LNbitsAdapter(config))
        proposal = proposal_manager.reject_proposal(proposal_id, "manual_cli", reason)
        
        click.echo(f"Proposal {proposal_id} rejected successfully")
        click.echo(f"Status: {proposal.status}")
        
    except Exception as e:
        logger.error("Failed to reject proposal", error=str(e))
        click.echo(f"Error: {e}", err=True)


@proposals.command("stats")
@click.pass_context
def proposals_stats(ctx):
    """Show proposal statistics."""
    try:
        config = ctx.obj["config"]
        persistence = PersistenceManager()
        
        if not FundingProposalManager:
            click.echo("Funding proposal module not available", err=True)
            return
        
        proposal_manager = FundingProposalManager(config, persistence, LNbitsAdapter(config))
        stats = proposal_manager.get_proposal_statistics()
        
        click.echo("Funding Proposal Statistics:")
        click.echo(f"Total Proposals: {stats['total_proposals']}")
        click.echo(f"Total Requested: {stats['total_requested_sats']:,} sats")
        click.echo(f"Total Approved: {stats['total_approved_sats']:,} sats")
        click.echo(f"Approval Rate: {stats['approval_rate']:.1%}")
        click.echo(f"Average Requested Amount: {stats['average_requested_amount']:,} sats")
        
        click.echo("\nBy Status:")
        for status, count in stats['by_status'].items():
            click.echo(f"  {status}: {count}")
            
    except Exception as e:
        logger.error("Failed to get proposal statistics", error=str(e))
        click.echo(f"Error: {e}", err=True)


@proposals.command("expire")
@click.pass_context
def proposals_expire(ctx):
    """Manually trigger expiration of old proposals."""
    try:
        config = ctx.obj["config"]
        persistence = PersistenceManager()
        
        if not FundingProposalManager:
            click.echo("Funding proposal module not available", err=True)
            return
        
        proposal_manager = FundingProposalManager(config, persistence, LNbitsAdapter(config))
        expired_count = proposal_manager.expire_old_proposals()
        
        click.echo(f"Expired {expired_count} old proposals")
        
    except Exception as e:
        logger.error("Failed to expire proposals", error=str(e))
        click.echo(f"Error: {e}", err=True)


@main.command("webhook-server")
@click.pass_context
def webhook_server(ctx):
    """Start the webhook server to receive approval notifications from n8n."""
    try:
        config = ctx.obj["config"]
        
        if not all([FundingProposalManager, N8nAdapter, run_webhook_server]):
            click.echo("Webhook server components not available", err=True)
            return
        
        if not config.webhook_server_enabled:
            click.echo("Webhook server is disabled in configuration", err=True)
            return
        
        persistence = PersistenceManager()
        proposal_manager = FundingProposalManager(config, persistence, LNbitsAdapter(config))
        n8n_adapter = N8nAdapter(config)
        
        click.echo(f"Starting webhook server on {config.webhook_server_host}:{config.webhook_server_port}")
        click.echo("Press Ctrl+C to stop")
        
        try:
            run_webhook_server(config, proposal_manager, n8n_adapter)
        except KeyboardInterrupt:
            click.echo("\nWebhook server stopped")
            
    except Exception as e:
        logger.error("Failed to start webhook server", error=str(e))
        click.echo(f"Error: {e}", err=True)


@main.command("api-server")
@click.option("--host", default="0.0.0.0", help="Host to bind the API server")
@click.option("--port", default=8000, type=int, help="Port for the API server")
@click.pass_context
def api_server(ctx, host: str, port: int):
    """Start the test API server for OpenClaw integration."""
    try:
        config = ctx.obj["config"]

        if run_api_server is None:
            click.echo("API server module not available", err=True)
            return

        click.echo(f"Starting test API server on {host}:{port}")
        click.echo("Press Ctrl+C to stop")

        try:
            run_api_server(config, host=host, port=port)
        except KeyboardInterrupt:
            click.echo("\nAPI server stopped")

    except Exception as e:
        logger.error("Failed to start API server", error=str(e))
        click.echo(f"Error: {e}", err=True)


@main.command("proposal-test")
@click.option("--amount", default=100000, help="Test proposal amount in sats")
@click.pass_context
def proposal_test(ctx, amount: int):
    """Test funding proposal generation and n8n integration."""
    try:
        config = ctx.obj["config"]
        persistence = PersistenceManager()
        
        if not all([FundingProposalManager, N8nAdapter]):
            click.echo("Funding proposal components not available", err=True)
            return
        
        proposal_manager = FundingProposalManager(config, persistence, LNbitsAdapter(config))
        n8n_adapter = N8nAdapter(config)
        
        # Create test AI context
        ai_context = {
            "current_balance_sats": 25000,  # Below threshold
            "market_conditions": {"opportunity_score": 0.8, "volatility": 0.3},
            "active_strategies": ["market_making", "arbitrage"],
            "recent_performance": {
                "daily_earnings": 5000,
                "success_rate": 0.75,
                "risk_level": "medium",
            },
            "decision_history": [],
        }
        
        # Generate test proposal
        proposal = proposal_manager.generate_proposal(ai_context)
        
        # Override the amount if specified
        if amount != 100000:  # Only override if different from default
            proposal.requested_amount_sats = amount
            # Recalculate expected ROI based on new amount
            proposal.expected_roi_sats = int(amount * 0.05)  # 5% ROI
            # Persist the updated proposal
            persistence.save_funding_proposal(proposal)
        
        click.echo(f"Generated test proposal: {proposal.proposal_id}")
        click.echo(f"Requested amount: {proposal.requested_amount_sats:,} sats")
        click.echo(f"Justification: {proposal.justification[:100]}...")
        
        # Send to n8n if configured
        if config.n8n_webhook_url:
            try:
                import asyncio
                response = asyncio.run(n8n_adapter.send_proposal(proposal))
                click.echo(f"Sent to n8n successfully: {response}")
            except Exception as e:
                click.echo(f"Failed to send to n8n: {e}")
        else:
            click.echo("n8n webhook URL not configured - skipping n8n test")
            
    except Exception as e:
        logger.error("Failed to test proposal", error=str(e))
        click.echo(f"Error: {e}", err=True)


if __name__ == "__main__":
    main()
