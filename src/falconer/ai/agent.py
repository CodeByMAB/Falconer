"""AI Agent for autonomous Bitcoin earning decisions using vLLM."""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from ..config import Config
from ..logging import get_logger
from ..persistence import PersistenceManager
from ..adapters.lnbits import LNbitsAdapter
from .decision_engine import DecisionEngine
from .earning_strategies import EarningStrategyManager
from .market_analyzer import MarketAnalyzer

logger = get_logger(__name__)

# Import funding modules here to avoid circular imports
try:
    from ..funding.manager import FundingProposalManager
    from ..funding.n8n_adapter import N8nAdapter
except ImportError:
    # Handle case where funding module is not available
    FundingProposalManager = None
    N8nAdapter = None


class AIAgentState(BaseModel):
    """Current state of the AI agent."""
    
    is_active: bool = False
    current_balance_sats: int = 0
    daily_earnings_sats: int = 0
    active_strategies: List[str] = []
    last_decision_time: Optional[datetime] = None
    risk_level: str = "medium"  # low, medium, high
    confidence_score: float = 0.0


class AIAgent:
    """AI Agent that makes autonomous decisions to earn Bitcoin using vLLM."""

    def __init__(self, config: Config):
        """Initialize the AI agent.

        Args:
            config: Falconer configuration
        """
        self.config = config
<<<<<<< HEAD
        self.vllm_model = getattr(config, "vllm_model", "llama3.1:8b")
        self.vllm_base_url = getattr(config, "vllm_base_url", "http://localhost:8000/v1")
=======
        self.ollama_model = config.ollama_model
        self.ollama_host = config.ollama_host
>>>>>>> b1a116d3a98b001a8622efcbb26f8c7486c0b6b6
        
        # Initialize components
        self.decision_engine = DecisionEngine(config)
        self.market_analyzer = MarketAnalyzer(config)
        self.strategy_manager = EarningStrategyManager(config)
        
        # Initialize persistence and adapters
        self.persistence = PersistenceManager()
        self.lnbits_adapter = LNbitsAdapter(config)
        
        # Initialize funding components if available
        if FundingProposalManager and N8nAdapter and config.funding_proposal_enabled:
            self.proposal_manager = FundingProposalManager(config, self.persistence, self.lnbits_adapter)
            self.n8n_adapter = N8nAdapter(config)
        else:
            self.proposal_manager = None
            self.n8n_adapter = None
        
        # Agent state
        self.state = AIAgentState()
        
        # Decision history for learning
        self.decision_history: List[Dict[str, Any]] = []
        
        logger.info(
            "AI Agent initialized",
            model=self.vllm_model,
            base_url=self.vllm_base_url,
        )
    
    async def start_autonomous_mode(self) -> None:
        """Start the autonomous earning mode."""
        logger.info("Starting autonomous earning mode")
        self.state.is_active = True
        
        # Main autonomous loop
        while self.state.is_active:
            try:
                await self._autonomous_cycle()
                # Wait 5 minutes between decision cycles
                await asyncio.sleep(300)
            except Exception as e:
                logger.error("Error in autonomous cycle", error=str(e))
                await asyncio.sleep(60)  # Wait 1 minute on error
    
    async def stop_autonomous_mode(self) -> None:
        """Stop the autonomous earning mode."""
        logger.info("Stopping autonomous earning mode")
        self.state.is_active = False
    
    async def _autonomous_cycle(self) -> None:
        """Execute one autonomous decision cycle."""
        logger.info("Starting autonomous decision cycle")
        
        # 0. Expire old proposals first
        await self._expire_old_proposals()
        
        # 1. Gather market intelligence
        market_data = await self.market_analyzer.analyze_current_conditions()
        
        # 2. Get current balance and earnings
        await self._update_agent_state(market_data)
        
        # 3. Make AI decision
        decision = await self._make_ai_decision(market_data)
        
        # 4. Execute decision if approved
        if decision and decision.get("action") != "wait":
            await self._execute_decision(decision)
        
        # 5. Update state
        self.state.last_decision_time = datetime.utcnow()
        
        logger.info("Autonomous cycle completed", decision=decision)
    
    async def _update_agent_state(self, market_data: Dict[str, Any]) -> None:
        """Update the agent's current state."""
        try:
            # Get current balance from LNbits
            try:
                balance_info = await asyncio.to_thread(self.lnbits_adapter.get_wallet_balance)
                self.state.current_balance_sats = balance_info.get("balance", 0)
            except Exception as e:
                logger.warning("Failed to get balance from LNbits", error=str(e))
                self.state.current_balance_sats = 0
            
            # Calculate daily earnings (placeholder for now)
            self.state.daily_earnings_sats = 0
            
            # Update risk level based on recent performance
            if len(self.decision_history) > 0:
                recent_success_rate = self._calculate_recent_success_rate()
                if recent_success_rate > 0.8:
                    self.state.risk_level = "low"
                elif recent_success_rate > 0.6:
                    self.state.risk_level = "medium"
                else:
                    self.state.risk_level = "high"
            
            # Check if funding proposal should be created
            if (self.proposal_manager and 
                self.config.funding_proposal_enabled and
                self.proposal_manager.should_create_proposal(self.state.current_balance_sats)):
                
                # Check if we're under the max pending limit
                pending_proposals = self.proposal_manager.list_proposals(status="pending")
                if len(pending_proposals) < self.config.funding_proposal_max_pending:
                    await self._generate_and_send_funding_proposal(market_data)
            
        except Exception as e:
            logger.error("Failed to update agent state", error=str(e))
    
    async def _make_ai_decision(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Use vLLM to make an AI decision about earning opportunities."""
        try:
            # Prepare context for the AI
            context = self._prepare_decision_context(market_data)

            # Create prompt for vLLM
            prompt = self._create_decision_prompt(context)

            # Get AI decision from vLLM
            response = await self._query_vllm(prompt)
            
            # Parse and validate the decision
            decision = self._parse_ai_decision(response)
            
            # Log the decision
            self.decision_history.append({
                "timestamp": datetime.utcnow().isoformat(),
                "context": context,
                "prompt": prompt,
                "response": response,
                "decision": decision
            })
            
            return decision
            
        except Exception as e:
            logger.error("Failed to make AI decision", error=str(e))
            return None
    
    def _prepare_decision_context(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare context data for AI decision making."""
        return {
            "current_time": datetime.utcnow().isoformat(),
            "agent_state": self.state.dict(),
            "market_data": market_data,
            "available_strategies": self.strategy_manager.get_available_strategies(),
            "recent_decisions": self.decision_history[-5:] if self.decision_history else [],
            "policy_limits": {
                "max_daily_spend": self.config.max_daily_spend_sats,
                "max_single_tx": self.config.max_single_tx_sats
            }
        }
    
    def _create_decision_prompt(self, context: Dict[str, Any]) -> str:
        """Create a prompt for vLLM to make earning decisions."""
        return f"""
You are Falconer, a Bitcoin-native AI agent designed to autonomously earn Bitcoin through micro-services and intelligent market analysis.

Current Context:
- Time: {context['current_time']}
- Current Balance: {context['agent_state']['current_balance_sats']} sats
- Daily Earnings: {context['agent_state']['daily_earnings_sats']} sats
- Risk Level: {context['agent_state']['risk_level']}
- Market Conditions: {json.dumps(context['market_data'], indent=2)}

Available Earning Strategies:
{json.dumps(context['available_strategies'], indent=2)}

Policy Limits:
- Max Daily Spend: {context['policy_limits']['max_daily_spend']} sats
- Max Single Transaction: {context['policy_limits']['max_single_tx']} sats

Recent Decisions:
{json.dumps(context['recent_decisions'], indent=2)}

Your task is to decide what action to take to earn Bitcoin. Consider:
1. Current market conditions and fee rates
2. Available earning strategies
3. Risk tolerance and policy limits
4. Recent performance and learning

Respond with a JSON object containing:
{{
    "action": "create_service|adjust_pricing|wait|analyze_market",
    "strategy": "strategy_name",
    "reasoning": "explanation of decision",
    "confidence": 0.0-1.0,
    "expected_earnings": estimated_sats,
    "risk_assessment": "low|medium|high",
    "parameters": {{"key": "value"}}
}}

If you decide to wait, set action to "wait" and explain why.
"""
    
    async def _query_vllm(self, prompt: str) -> str:
        """Query vLLM (OpenAI-compatible API) with the decision prompt."""
        try:
            client = AsyncOpenAI(
                base_url=self.vllm_base_url,
                api_key="dummy",  # vLLM often does not require a key
            )
            response = await client.chat.completions.create(
                model=self.vllm_model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are Falconer, a Bitcoin-native AI agent. Always respond with valid JSON.",
                    },
                    {"role": "user", "content": prompt},
                ],
            )
            content = response.choices[0].message.content
            return content or ""
        except Exception as e:
            logger.error("Failed to query vLLM", error=str(e))
            raise
    
    def _parse_ai_decision(self, response: str) -> Optional[Dict[str, Any]]:
        """Parse and validate the AI decision response."""
        try:
            # Try to parse the entire response as JSON first
            try:
                decision = json.loads(response)
                if isinstance(decision, dict):
                    # Successfully parsed entire response as JSON
                    pass
                else:
                    raise ValueError("Response is not a JSON object")
            except (json.JSONDecodeError, ValueError):
                # Extract JSON from response using balanced brace matching
                json_start = response.find('{')
                if json_start == -1:
                    logger.warning("No JSON found in AI response", response=response)
                    return None

                # Find matching closing brace
                brace_count = 0
                json_end = json_start
                for i in range(json_start, len(response)):
                    if response[i] == '{':
                        brace_count += 1
                    elif response[i] == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            json_end = i + 1
                            break

                if brace_count != 0:
                    logger.warning("Unbalanced braces in AI response", response=response)
                    return None

                json_str = response[json_start:json_end]
                decision = json.loads(json_str)
            
            # Validate required fields
            required_fields = ['action', 'reasoning', 'confidence']
            for field in required_fields:
                if field not in decision:
                    logger.warning(f"Missing required field in AI decision: {field}")
                    return None
            
            # Validate action
            valid_actions = ['create_service', 'adjust_pricing', 'wait', 'analyze_market']
            if decision['action'] not in valid_actions:
                logger.warning(f"Invalid action in AI decision: {decision['action']}")
                return None
            
            return decision
            
        except json.JSONDecodeError as e:
            logger.error("Failed to parse AI decision JSON", error=str(e), response=response)
            return None
        except Exception as e:
            logger.error("Failed to parse AI decision", error=str(e))
            return None
    
    async def _execute_decision(self, decision: Dict[str, Any]) -> None:
        """Execute the AI decision."""
        try:
            action = decision['action']
            strategy = decision.get('strategy')
            parameters = decision.get('parameters', {})
            
            logger.info("Executing AI decision", action=action, strategy=strategy)
            
            if action == 'create_service':
                await self.strategy_manager.execute_strategy(strategy, parameters)
            elif action == 'adjust_pricing':
                await self.strategy_manager.adjust_pricing(strategy, parameters)
            elif action == 'analyze_market':
                await self.market_analyzer.perform_deep_analysis()
            
            # Update confidence score based on decision
            self.state.confidence_score = decision.get('confidence', 0.5)
            
        except Exception as e:
            logger.error("Failed to execute AI decision", error=str(e), decision=decision)
    
    def _calculate_recent_success_rate(self) -> float:
        """Calculate success rate of recent decisions."""
        if not self.decision_history:
            return 0.5  # Default neutral success rate
        
        # Look at last 10 decisions
        recent_decisions = self.decision_history[-10:]
        successful_decisions = 0
        
        for decision_record in recent_decisions:
            decision = decision_record.get('decision', {})
            if decision.get('action') != 'wait':
                # For now, consider non-wait decisions as successful
                # In a real implementation, you'd track actual outcomes
                successful_decisions += 1
        
        return successful_decisions / len(recent_decisions) if recent_decisions else 0.5
    
    async def get_agent_status(self) -> Dict[str, Any]:
        """Get current status of the AI agent."""
        return {
            "is_active": self.state.is_active,
            "model": self.vllm_model,
            "base_url": self.vllm_base_url,
            "state": self.state.dict(),
            "recent_decisions_count": len(self.decision_history),
            "last_decision_time": self.state.last_decision_time.isoformat() if self.state.last_decision_time else None
        }

    async def _generate_and_send_funding_proposal(self, market_data: Dict[str, Any]) -> None:
        """Generate and send a funding proposal when balance is low."""
        if not self.proposal_manager or not self.n8n_adapter:
            logger.warning("Funding proposal components not available")
            return
        
        try:
            # Prepare AI context for proposal generation
            ai_context = {
                "current_balance_sats": self.state.current_balance_sats,
                "market_conditions": market_data,  # Use already computed market data
                "active_strategies": self.state.active_strategies,
                "recent_performance": {
                    "daily_earnings": self.state.daily_earnings_sats,
                    "success_rate": self._calculate_recent_success_rate(),
                    "risk_level": self.state.risk_level,
                },
                "decision_history": self.decision_history[-5:],  # Last 5 decisions
            }
            
            # Generate proposal
            proposal = self.proposal_manager.generate_proposal(ai_context)
            
            # Send to n8n
            response = await self.n8n_adapter.send_proposal(proposal)
            
            # Update proposal with n8n workflow ID if available
            if response.get("workflow_id"):
                proposal.n8n_workflow_id = response["workflow_id"]
                self.persistence.save_funding_proposal(proposal)
            
            logger.info(
                "Funding proposal generated and sent to n8n",
                proposal_id=proposal.proposal_id,
                requested_amount_sats=proposal.requested_amount_sats,
                workflow_id=response.get("workflow_id"),
            )
            
        except Exception as e:
            logger.error("Failed to generate and send funding proposal", error=str(e))

    async def _expire_old_proposals(self) -> None:
        """Expire old pending proposals."""
        if not self.proposal_manager:
            return
        
        try:
            expired_count = self.proposal_manager.expire_old_proposals(
                self.config.funding_proposal_expiry_hours
            )
            
            if expired_count > 0:
                logger.info("Expired old funding proposals", count=expired_count)
                
        except Exception as e:
            logger.error("Failed to expire old proposals", error=str(e))
