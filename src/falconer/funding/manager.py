"""Funding proposal manager for handling proposal lifecycle."""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from ..config import Config
from ..persistence import PersistenceManager
from ..adapters.lnbits import LNbitsAdapter
from .schema import FundingProposal, ProposalSummary


class FundingProposalManager:
    """Manages funding proposal lifecycle and operations."""
    
    def __init__(self, config: Config, persistence: PersistenceManager, lnbits_adapter: LNbitsAdapter):
        """Initialize the funding proposal manager."""
        self.config = config
        self.persistence = persistence
        self.lnbits_adapter = lnbits_adapter
    
    def should_create_proposal(self, current_balance_sats: int) -> bool:
        """Check if balance is below threshold and proposal should be generated."""
        if not self.config.funding_proposal_enabled:
            return False
        
        threshold = self.config.funding_proposal_threshold_sats
        return current_balance_sats < threshold
    
    def generate_proposal(self, ai_context: Dict[str, Any]) -> FundingProposal:
        """Create a new funding proposal using AI context."""
        # Check if we're at max pending proposals
        pending_proposals = self.list_proposals(status="pending")
        if len(pending_proposals) >= self.config.funding_proposal_max_pending:
            raise ValueError(f"Maximum pending proposals ({self.config.funding_proposal_max_pending}) reached")
        
        # Extract context data
        current_balance = ai_context.get("current_balance_sats", 0)
        market_conditions = ai_context.get("market_conditions", {})
        active_strategies = ai_context.get("active_strategies", [])
        recent_performance = ai_context.get("recent_performance", {})
        
        # Calculate requested amount
        requested_amount = self.config.funding_proposal_default_amount_sats
        
        # Generate justification based on AI context
        justification = self._generate_justification(
            current_balance, market_conditions, active_strategies, recent_performance
        )
        
        # Generate intended use plan
        intended_use = self._generate_intended_use(active_strategies, market_conditions)
        
        # Calculate expected ROI
        expected_roi = self._calculate_expected_roi(requested_amount, active_strategies, recent_performance)
        
        # Assess risk level
        risk_assessment = self._assess_risk(market_conditions, active_strategies)
        
        # Create proposal
        proposal = FundingProposal(
            requested_amount_sats=requested_amount,
            current_balance_sats=current_balance,
            justification=justification,
            intended_use=intended_use,
            expected_roi_sats=expected_roi,
            risk_assessment=risk_assessment,
            strategies_to_execute=active_strategies,
            time_horizon_days=self._calculate_time_horizon(active_strategies),
        )
        
        # Save proposal
        self.persistence.save_funding_proposal(proposal)
        
        return proposal
    
    def get_proposal(self, proposal_id: str) -> Optional[FundingProposal]:
        """Load proposal from persistence by ID."""
        return self.persistence.load_funding_proposal(proposal_id)
    
    def list_proposals(self, status: Optional[str] = None, limit: int = 50) -> List[ProposalSummary]:
        """List proposals, optionally filtered by status."""
        proposals = self.persistence.load_funding_proposals(status=status, limit=limit)
        
        summaries = []
        for proposal in proposals:
            # Truncate justification to 200 chars
            justification = proposal.justification
            if len(justification) > 200:
                justification = justification[:197] + "..."
            
            summary = ProposalSummary(
                proposal_id=proposal.proposal_id,
                created_at=proposal.created_at,
                status=proposal.status,
                requested_amount_sats=proposal.requested_amount_sats,
                justification=justification,
            )
            summaries.append(summary)
        
        return summaries
    
    def approve_proposal(self, proposal_id: str, approved_by: str, notes: Optional[str] = None) -> FundingProposal:
        """Update proposal status to 'approved'."""
        proposal = self.get_proposal(proposal_id)
        if not proposal:
            raise ValueError(f"Proposal {proposal_id} not found")
        
        if proposal.status != "pending":
            raise ValueError(f"Proposal {proposal_id} is not in pending status (current: {proposal.status})")
        
        proposal.status = "approved"
        proposal.approved_at = datetime.utcnow()
        proposal.approved_by = approved_by
        
        # Store approval notes
        if notes:
            proposal.approval_notes = notes
        
        self.persistence.save_funding_proposal(proposal)
        return proposal
    
    def reject_proposal(self, proposal_id: str, rejected_by: str, reason: str) -> FundingProposal:
        """Update proposal status to 'rejected'."""
        proposal = self.get_proposal(proposal_id)
        if not proposal:
            raise ValueError(f"Proposal {proposal_id} not found")
        
        if proposal.status != "pending":
            raise ValueError(f"Proposal {proposal_id} is not in pending status (current: {proposal.status})")
        
        proposal.status = "rejected"
        proposal.rejected_at = datetime.utcnow()
        proposal.rejected_by = rejected_by
        proposal.approval_notes = reason
        
        self.persistence.save_funding_proposal(proposal)
        return proposal
    
    def mark_executed(self, proposal_id: str, txid: str) -> FundingProposal:
        """Update proposal status to 'executed'."""
        proposal = self.get_proposal(proposal_id)
        if not proposal:
            raise ValueError(f"Proposal {proposal_id} not found")
        
        if proposal.status != "approved":
            raise ValueError(f"Proposal {proposal_id} is not approved (current: {proposal.status})")
        
        proposal.status = "executed"
        proposal.executed_at = datetime.utcnow()
        proposal.execution_txid = txid
        
        self.persistence.save_funding_proposal(proposal)
        return proposal
    
    def expire_old_proposals(self, max_age_hours: int = 24) -> int:
        """Find proposals in 'pending' status older than max_age_hours and mark as 'expired'."""
        cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
        pending_proposals = self.persistence.load_funding_proposals(status="pending")
        
        expired_count = 0
        for proposal in pending_proposals:
            if proposal.created_at < cutoff_time:
                proposal.status = "expired"
                self.persistence.save_funding_proposal(proposal)
                expired_count += 1
        
        return expired_count
    
    def get_proposal_statistics(self) -> Dict[str, Any]:
        """Return statistics about proposals."""
        all_proposals = self.persistence.load_funding_proposals()
        
        stats = {
            "total_proposals": len(all_proposals),
            "by_status": {},
            "total_requested_sats": 0,
            "total_approved_sats": 0,
            "approval_rate": 0.0,
            "average_requested_amount": 0,
        }
        
        if not all_proposals:
            return stats
        
        # Count by status
        for proposal in all_proposals:
            status = proposal.status
            stats["by_status"][status] = stats["by_status"].get(status, 0) + 1
            stats["total_requested_sats"] += proposal.requested_amount_sats
            
            if status == "approved":
                stats["total_approved_sats"] += proposal.requested_amount_sats
        
        # Calculate approval rate using decided proposals only (approved + rejected)
        decided = stats["by_status"].get("approved", 0) + stats["by_status"].get("rejected", 0)
        if decided > 0:
            stats["approval_rate"] = stats["by_status"].get("approved", 0) / decided
        
        # Calculate average requested amount
        stats["average_requested_amount"] = stats["total_requested_sats"] // len(all_proposals)
        
        return stats
    
    def _generate_justification(self, current_balance: int, market_conditions: Dict, 
                              active_strategies: List[str], recent_performance: Dict) -> str:
        """Generate AI justification for funding request."""
        justification_parts = [
            f"Current balance of {current_balance:,} sats is insufficient for optimal earning operations.",
        ]
        
        if active_strategies:
            justification_parts.append(f"Active strategies: {', '.join(active_strategies)} require additional capital.")
        
        if market_conditions.get("opportunity_score", 0) > 0.7:
            justification_parts.append("Market conditions show high earning opportunities that require immediate capital deployment.")
        
        if recent_performance.get("daily_earnings", 0) > 0:
            justification_parts.append(f"Recent performance shows {recent_performance['daily_earnings']:,} sats daily earnings potential.")
        
        justification_parts.append("Additional funding will enable increased earning capacity and strategy diversification.")
        
        return " ".join(justification_parts)
    
    def _generate_intended_use(self, active_strategies: List[str], market_conditions: Dict) -> str:
        """Generate detailed plan for how funds will be used."""
        use_parts = [
            "The requested funds will be deployed across multiple earning strategies:",
        ]
        
        if active_strategies:
            for strategy in active_strategies:
                use_parts.append(f"- {strategy}: Allocate capital based on market conditions and risk assessment")
        else:
            use_parts.append("- Market making: Provide liquidity to earn spread profits")
            use_parts.append("- Arbitrage: Capture price differences across exchanges")
            use_parts.append("- Yield farming: Earn rewards from DeFi protocols")
        
        use_parts.append("Funds will be managed with strict risk controls and monitored continuously.")
        
        return " ".join(use_parts)
    
    def _calculate_expected_roi(self, requested_amount: int, active_strategies: List[str], 
                              recent_performance: Dict) -> int:
        """Calculate expected return on investment."""
        # Base ROI of 5% over 30 days
        base_roi_rate = 0.05
        
        # Adjust based on recent performance
        if recent_performance.get("daily_earnings", 0) > 0:
            daily_rate = recent_performance["daily_earnings"] / requested_amount
            base_roi_rate = max(base_roi_rate, daily_rate * 30)  # 30-day projection
        
        # Adjust based on number of strategies (more strategies = higher potential)
        strategy_multiplier = 1.0 + (len(active_strategies) * 0.1)
        
        expected_roi = int(requested_amount * base_roi_rate * strategy_multiplier)
        return expected_roi
    
    def _assess_risk(self, market_conditions: Dict, active_strategies: List[str]) -> str:
        """Assess risk level based on market conditions and strategies."""
        risk_score = 0.5  # Base medium risk
        
        # Adjust based on market volatility
        volatility = market_conditions.get("volatility", 0.5)
        risk_score += (volatility - 0.5) * 0.3
        
        # Adjust based on number of strategies (more strategies = lower risk)
        if len(active_strategies) > 3:
            risk_score -= 0.2
        elif len(active_strategies) < 2:
            risk_score += 0.2
        
        # Clamp to valid range
        risk_score = max(0.0, min(1.0, risk_score))
        
        if risk_score < 0.3:
            return "low"
        elif risk_score < 0.7:
            return "medium"
        else:
            return "high"
    
    def _calculate_time_horizon(self, active_strategies: List[str]) -> int:
        """Calculate expected timeframe for ROI."""
        if not active_strategies:
            return 30  # Default 30 days
        
        # Different strategies have different time horizons
        strategy_horizons = {
            "market_making": 7,
            "arbitrage": 1,
            "yield_farming": 30,
            "liquidity_provision": 14,
        }
        
        # Use the longest horizon among active strategies
        max_horizon = 30  # Default
        for strategy in active_strategies:
            horizon = strategy_horizons.get(strategy.lower(), 30)
            max_horizon = max(max_horizon, horizon)
        
        return max_horizon
