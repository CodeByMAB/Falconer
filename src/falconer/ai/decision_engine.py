"""Decision engine for AI agent decision making."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from ..config import Config
from ..logging import get_logger
from .market_analyzer import MarketCondition
from .earning_strategies import EarningStrategy

logger = get_logger(__name__)


class DecisionContext(BaseModel):
    """Context for AI decision making."""
    
    market_condition: MarketCondition
    available_strategies: List[EarningStrategy]
    current_balance_sats: int
    daily_earnings_sats: int
    risk_tolerance: str
    policy_limits: Dict[str, int]
    recent_performance: Dict[str, float]


class Decision(BaseModel):
    """AI decision result."""
    
    action: str
    strategy: Optional[str] = None
    reasoning: str
    confidence: float
    expected_earnings: int
    risk_assessment: str
    parameters: Dict[str, Any] = {}


class DecisionEngine:
    """Engine for making AI-driven decisions about earning opportunities."""
    
    def __init__(self, config: Config):
        """Initialize the decision engine.
        
        Args:
            config: Falconer configuration
        """
        self.config = config
        self.decision_history: List[Decision] = []
        
        logger.info("Decision Engine initialized")
    
    def make_decision(self, context: DecisionContext) -> Decision:
        """Make a decision based on the current context."""
        try:
            logger.info("Making AI decision", 
                       market_opportunity_score=context.market_condition.opportunity_score,
                       available_strategies=len(context.available_strategies))
            
            # Analyze market conditions
            if context.market_condition.opportunity_score > 0.7:
                decision = self._make_high_opportunity_decision(context)
            elif context.market_condition.opportunity_score > 0.4:
                decision = self._make_medium_opportunity_decision(context)
            else:
                decision = self._make_low_opportunity_decision(context)
            
            # Store decision in history
            self.decision_history.append(decision)
            
            # Keep only last 100 decisions
            if len(self.decision_history) > 100:
                self.decision_history = self.decision_history[-100:]
            
            logger.info("Decision made", 
                       action=decision.action,
                       strategy=decision.strategy,
                       confidence=decision.confidence)
            
            return decision
            
        except Exception as e:
            logger.error("Failed to make decision", error=str(e))
            # Return safe default decision
            return Decision(
                action="wait",
                reasoning="Error in decision making, taking safe approach",
                confidence=0.1,
                expected_earnings=0,
                risk_assessment="high"
            )
    
    def _make_high_opportunity_decision(self, context: DecisionContext) -> Decision:
        """Make decision when market opportunity is high."""
        # Find best strategy for high opportunity
        best_strategy = self._find_best_strategy(context, min_expected_earnings=1000)
        
        if best_strategy:
            return Decision(
                action="create_service",
                strategy=best_strategy.name,
                reasoning=f"High market opportunity ({context.market_condition.opportunity_score:.2f}) detected. {best_strategy.description}",
                confidence=0.8,
                expected_earnings=best_strategy.base_price_sats,
                risk_assessment=best_strategy.risk_level,
                parameters={
                    "urgency": "high",
                    "pricing_multiplier": 1.2  # Premium pricing for high demand
                }
            )
        else:
            return Decision(
                action="analyze_market",
                reasoning="High opportunity detected but no suitable strategy available",
                confidence=0.6,
                expected_earnings=0,
                risk_assessment="medium"
            )
    
    def _make_medium_opportunity_decision(self, context: DecisionContext) -> Decision:
        """Make decision when market opportunity is medium."""
        # Find strategy for medium opportunity
        best_strategy = self._find_best_strategy(context, min_expected_earnings=500)
        
        if best_strategy:
            return Decision(
                action="create_service",
                strategy=best_strategy.name,
                reasoning=f"Medium market opportunity ({context.market_condition.opportunity_score:.2f}) detected. {best_strategy.description}",
                confidence=0.6,
                expected_earnings=best_strategy.base_price_sats,
                risk_assessment=best_strategy.risk_level,
                parameters={
                    "urgency": "medium",
                    "pricing_multiplier": 1.0  # Standard pricing
                }
            )
        else:
            return Decision(
                action="wait",
                reasoning="Medium opportunity but no suitable strategy available",
                confidence=0.5,
                expected_earnings=0,
                risk_assessment="low"
            )
    
    def _make_low_opportunity_decision(self, context: DecisionContext) -> Decision:
        """Make decision when market opportunity is low."""
        # In low opportunity scenarios, focus on low-risk strategies
        low_risk_strategies = [s for s in context.available_strategies if s.risk_level == "low"]
        
        if low_risk_strategies and context.daily_earnings_sats < context.policy_limits.get("max_daily_spend_sats", 100000) * 0.1:
            # Only create services if we haven't earned much today
            best_strategy = min(low_risk_strategies, key=lambda s: s.base_price_sats)
            
            return Decision(
                action="create_service",
                strategy=best_strategy.name,
                reasoning=f"Low opportunity but creating low-risk service to maintain activity",
                confidence=0.4,
                expected_earnings=best_strategy.base_price_sats,
                risk_assessment="low",
                parameters={
                    "urgency": "low",
                    "pricing_multiplier": 0.8  # Discount pricing for low demand
                }
            )
        else:
            return Decision(
                action="wait",
                reasoning="Low market opportunity, waiting for better conditions",
                confidence=0.7,
                expected_earnings=0,
                risk_assessment="low"
            )
    
    def _find_best_strategy(self, context: DecisionContext, min_expected_earnings: int = 0) -> Optional[EarningStrategy]:
        """Find the best strategy based on context and requirements."""
        suitable_strategies = []
        
        for strategy in context.available_strategies:
            # Check if strategy meets minimum earnings requirement
            if strategy.base_price_sats < min_expected_earnings:
                continue
            
            # Check risk tolerance
            if context.risk_tolerance == "low" and strategy.risk_level != "low":
                continue
            elif context.risk_tolerance == "medium" and strategy.risk_level == "high":
                continue
            
            # Check if we have the required balance
            if strategy.base_price_sats > context.current_balance_sats:
                continue
            
            suitable_strategies.append(strategy)
        
        if not suitable_strategies:
            return None
        
        # Score strategies based on multiple factors
        best_strategy = None
        best_score = -1
        
        for strategy in suitable_strategies:
            score = self._score_strategy(strategy, context)
            if score > best_score:
                best_score = score
                best_strategy = strategy
        
        return best_strategy
    
    def _score_strategy(self, strategy: EarningStrategy, context: DecisionContext) -> float:
        """Score a strategy based on multiple factors."""
        score = 0.0
        
        # Base score from success rate
        score += strategy.success_rate * 0.4
        
        # Earnings potential
        earnings_ratio = strategy.base_price_sats / max(context.current_balance_sats, 1)
        score += min(earnings_ratio, 1.0) * 0.3
        
        # Risk adjustment
        if strategy.risk_level == "low":
            score += 0.2
        elif strategy.risk_level == "medium":
            score += 0.1
        # High risk gets no bonus
        
        # Recent usage penalty (avoid overusing same strategy)
        if strategy.last_used:
            time_since_last_use = datetime.utcnow() - strategy.last_used
            if time_since_last_use.total_seconds() < 3600:  # Less than 1 hour
                score -= 0.1
        
        return score
    
    def get_decision_history(self, limit: int = 10) -> List[Decision]:
        """Get recent decision history."""
        return self.decision_history[-limit:] if self.decision_history else []
    
    def get_decision_statistics(self) -> Dict[str, Any]:
        """Get statistics about decision making performance."""
        if not self.decision_history:
            return {"total_decisions": 0}
        
        total_decisions = len(self.decision_history)
        action_counts = {}
        strategy_counts = {}
        total_expected_earnings = 0
        total_confidence = 0
        
        for decision in self.decision_history:
            # Count actions
            action_counts[decision.action] = action_counts.get(decision.action, 0) + 1
            
            # Count strategies
            if decision.strategy:
                strategy_counts[decision.strategy] = strategy_counts.get(decision.strategy, 0) + 1
            
            # Sum earnings and confidence
            total_expected_earnings += decision.expected_earnings
            total_confidence += decision.confidence
        
        return {
            "total_decisions": total_decisions,
            "action_distribution": action_counts,
            "strategy_distribution": strategy_counts,
            "average_expected_earnings": total_expected_earnings / total_decisions,
            "average_confidence": total_confidence / total_decisions,
            "most_common_action": max(action_counts.items(), key=lambda x: x[1])[0] if action_counts else None,
            "most_common_strategy": max(strategy_counts.items(), key=lambda x: x[1])[0] if strategy_counts else None
        }
