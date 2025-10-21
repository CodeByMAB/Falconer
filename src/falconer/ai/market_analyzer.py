"""AI-powered market analysis for Bitcoin earning opportunities."""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from pydantic import BaseModel

from ..adapters.bitcoind import BitcoinAdapter
from ..adapters.electrs import ElectrsAdapter
from ..adapters.mempool import MempoolAdapter
from ..config import Config
from ..logging import get_logger

logger = get_logger(__name__)


class MarketCondition(BaseModel):
    """Market condition analysis result."""
    
    timestamp: datetime
    fee_trend: str  # "rising", "falling", "stable"
    mempool_congestion: str  # "low", "medium", "high", "critical"
    network_activity: str  # "low", "normal", "high"
    opportunity_score: float  # 0.0 to 1.0
    recommended_actions: List[str]
    confidence: float


class EarningOpportunity(BaseModel):
    """Identified earning opportunity."""
    
    opportunity_type: str
    description: str
    potential_earnings_sats: int
    risk_level: str
    time_sensitivity: str  # "immediate", "short_term", "long_term"
    requirements: List[str]
    confidence: float


class MarketAnalyzer:
    """AI-powered market analyzer for Bitcoin earning opportunities."""
    
    def __init__(self, config: Config):
        """Initialize the market analyzer.
        
        Args:
            config: Falconer configuration
        """
        self.config = config
        self.bitcoin_adapter = BitcoinAdapter(config)
        self.electrs_adapter = ElectrsAdapter(config)
        self.mempool_adapter = MempoolAdapter()
        
        # Historical data for trend analysis
        self.fee_history: List[Dict[str, Any]] = []
        self.mempool_history: List[Dict[str, Any]] = []
        self.opportunity_history: List[EarningOpportunity] = []
        
        logger.info("Market Analyzer initialized")
    
    async def analyze_current_conditions(self) -> MarketCondition:
        """Analyze current market conditions for earning opportunities."""
        try:
            logger.info("Analyzing current market conditions")
            
            # Gather current data
            current_data = await self._gather_market_data()
            
            # Analyze trends
            trends = self._analyze_trends(current_data)
            
            # Calculate opportunity score
            opportunity_score = self._calculate_opportunity_score(current_data, trends)
            
            # Generate recommendations
            recommendations = self._generate_recommendations(current_data, trends, opportunity_score)
            
            # Create market condition
            condition = MarketCondition(
                timestamp=datetime.utcnow(),
                fee_trend=trends['fee_trend'],
                mempool_congestion=trends['mempool_congestion'],
                network_activity=trends['network_activity'],
                opportunity_score=opportunity_score,
                recommended_actions=recommendations,
                confidence=self._calculate_confidence(current_data, trends)
            )
            
            logger.info("Market analysis completed", 
                       opportunity_score=opportunity_score,
                       fee_trend=trends['fee_trend'],
                       mempool_congestion=trends['mempool_congestion'])
            
            return condition
            
        except Exception as e:
            logger.error("Failed to analyze market conditions", error=str(e))
            # Return default condition on error
            return MarketCondition(
                timestamp=datetime.utcnow(),
                fee_trend="stable",
                mempool_congestion="medium",
                network_activity="normal",
                opportunity_score=0.5,
                recommended_actions=["wait"],
                confidence=0.3
            )
    
    async def _gather_market_data(self) -> Dict[str, Any]:
        """Gather current market data from various sources."""
        data = {}
        
        try:
            # Get Bitcoin Core data
            blockchain_info = self.bitcoin_adapter.get_blockchain_info()
            mempool_info = self.bitcoin_adapter.get_mempool_info()
            
            # Get fee estimates
            fee_estimates = {}
            for target in [1, 3, 6, 12, 24]:
                try:
                    estimate = self.bitcoin_adapter.estimate_smart_fee(target)
                    if "feerate" in estimate:
                        fee_estimates[f"{target}_block"] = estimate["feerate"] * 100000  # Convert to sats/vbyte
                except Exception as e:
                    logger.warning(f"Failed to get fee estimate for {target} blocks", error=str(e))
            
            # Get mempool data
            mempool_tip = await self.mempool_adapter.tip_height()
            
            data.update({
                "blockchain_info": blockchain_info,
                "mempool_info": mempool_info,
                "fee_estimates": fee_estimates,
                "mempool_tip": mempool_tip,
                "timestamp": datetime.utcnow()
            })
            
        except Exception as e:
            logger.error("Failed to gather market data", error=str(e))
            data = {"error": str(e), "timestamp": datetime.utcnow()}
        
        return data
    
    def _analyze_trends(self, current_data: Dict[str, Any]) -> Dict[str, str]:
        """Analyze trends from current and historical data."""
        trends = {
            "fee_trend": "stable",
            "mempool_congestion": "medium",
            "network_activity": "normal"
        }
        
        try:
            # Analyze fee trends
            if "fee_estimates" in current_data:
                current_6_block_fee = current_data["fee_estimates"].get("6_block", 0)
                
                if len(self.fee_history) >= 3:
                    recent_fees = [h.get("6_block_fee", 0) for h in self.fee_history[-3:]]
                    avg_recent_fee = np.mean(recent_fees)
                    
                    if current_6_block_fee > avg_recent_fee * 1.2:
                        trends["fee_trend"] = "rising"
                    elif current_6_block_fee < avg_recent_fee * 0.8:
                        trends["fee_trend"] = "falling"
                    else:
                        trends["fee_trend"] = "stable"
            
            # Analyze mempool congestion
            if "mempool_info" in current_data:
                mempool_info = current_data["mempool_info"]
                usage_percent = (mempool_info["usage"] / mempool_info["maxmempool"]) * 100
                
                if usage_percent > 80:
                    trends["mempool_congestion"] = "critical"
                elif usage_percent > 60:
                    trends["mempool_congestion"] = "high"
                elif usage_percent > 30:
                    trends["mempool_congestion"] = "medium"
                else:
                    trends["mempool_congestion"] = "low"
            
            # Analyze network activity
            if "blockchain_info" in current_data:
                # This is a simplified analysis - in reality you'd look at more metrics
                current_height = current_data["blockchain_info"]["blocks"]
                
                if len(self.mempool_history) >= 2:
                    recent_heights = [h.get("height", 0) for h in self.mempool_history[-2:]]
                    if len(recent_heights) >= 2:
                        height_diff = current_height - recent_heights[-1]
                        if height_diff > 2:
                            trends["network_activity"] = "high"
                        elif height_diff < 1:
                            trends["network_activity"] = "low"
                        else:
                            trends["network_activity"] = "normal"
            
        except Exception as e:
            logger.error("Failed to analyze trends", error=str(e))
        
        return trends
    
    def _calculate_opportunity_score(self, current_data: Dict[str, Any], trends: Dict[str, str]) -> float:
        """Calculate overall opportunity score (0.0 to 1.0)."""
        score = 0.5  # Base score
        
        try:
            # Fee trend scoring
            if trends["fee_trend"] == "rising":
                score += 0.2  # High fees = more earning potential
            elif trends["fee_trend"] == "falling":
                score -= 0.1  # Low fees = less earning potential
            
            # Mempool congestion scoring
            if trends["mempool_congestion"] == "critical":
                score += 0.3  # High congestion = high demand for services
            elif trends["mempool_congestion"] == "high":
                score += 0.2
            elif trends["mempool_congestion"] == "low":
                score -= 0.1
            
            # Network activity scoring
            if trends["network_activity"] == "high":
                score += 0.1  # High activity = more opportunities
            elif trends["network_activity"] == "low":
                score -= 0.1
            
            # Ensure score is between 0.0 and 1.0
            score = max(0.0, min(1.0, score))
            
        except Exception as e:
            logger.error("Failed to calculate opportunity score", error=str(e))
        
        return score
    
    def _generate_recommendations(self, current_data: Dict[str, Any], trends: Dict[str, str], opportunity_score: float) -> List[str]:
        """Generate actionable recommendations based on analysis."""
        recommendations = []
        
        try:
            # High opportunity scenarios
            if opportunity_score > 0.7:
                if trends["mempool_congestion"] in ["high", "critical"]:
                    recommendations.append("create_fee_intelligence_service")
                    recommendations.append("offer_mempool_monitoring")
                
                if trends["fee_trend"] == "rising":
                    recommendations.append("create_fee_optimization_service")
                    recommendations.append("offer_transaction_timing_advice")
            
            # Medium opportunity scenarios
            elif opportunity_score > 0.4:
                recommendations.append("create_standard_fee_brief")
                recommendations.append("monitor_for_opportunities")
            
            # Low opportunity scenarios
            else:
                recommendations.append("wait_for_better_conditions")
                recommendations.append("analyze_historical_patterns")
            
            # Always include basic recommendations
            recommendations.append("update_pricing_strategy")
            recommendations.append("track_performance_metrics")
            
        except Exception as e:
            logger.error("Failed to generate recommendations", error=str(e))
            recommendations = ["wait"]
        
        return recommendations
    
    def _calculate_confidence(self, current_data: Dict[str, Any], trends: Dict[str, str]) -> float:
        """Calculate confidence in the analysis (0.0 to 1.0)."""
        confidence = 0.5  # Base confidence
        
        try:
            # More data points = higher confidence
            if len(self.fee_history) > 10:
                confidence += 0.2
            elif len(self.fee_history) > 5:
                confidence += 0.1
            
            if len(self.mempool_history) > 10:
                confidence += 0.2
            elif len(self.mempool_history) > 5:
                confidence += 0.1
            
            # Data quality affects confidence
            if "error" not in current_data:
                confidence += 0.1
            
            # Ensure confidence is between 0.0 and 1.0
            confidence = max(0.0, min(1.0, confidence))
            
        except Exception as e:
            logger.error("Failed to calculate confidence", error=str(e))
        
        return confidence
    
    async def identify_earning_opportunities(self) -> List[EarningOpportunity]:
        """Identify specific earning opportunities in the current market."""
        opportunities = []
        
        try:
            current_condition = await self.analyze_current_conditions()
            
            # Fee intelligence opportunity
            if current_condition.mempool_congestion in ["high", "critical"]:
                opportunities.append(EarningOpportunity(
                    opportunity_type="fee_intelligence",
                    description="High mempool congestion creates demand for fee intelligence services",
                    potential_earnings_sats=5000,  # 50k sats potential
                    risk_level="low",
                    time_sensitivity="immediate",
                    requirements=["fee_brief_generation", "mempool_analysis"],
                    confidence=0.8
                ))
            
            # Transaction optimization opportunity
            if current_condition.fee_trend == "rising":
                opportunities.append(EarningOpportunity(
                    opportunity_type="transaction_optimization",
                    description="Rising fees create demand for transaction optimization advice",
                    potential_earnings_sats=3000,
                    risk_level="low",
                    time_sensitivity="short_term",
                    requirements=["fee_estimation", "timing_analysis"],
                    confidence=0.7
                ))
            
            # Market analysis opportunity
            if current_condition.network_activity == "high":
                opportunities.append(EarningOpportunity(
                    opportunity_type="market_analysis",
                    description="High network activity indicates demand for market insights",
                    potential_earnings_sats=2000,
                    risk_level="low",
                    time_sensitivity="long_term",
                    requirements=["trend_analysis", "report_generation"],
                    confidence=0.6
                ))
            
            # Store opportunities for learning
            self.opportunity_history.extend(opportunities)
            
        except Exception as e:
            logger.error("Failed to identify earning opportunities", error=str(e))
        
        return opportunities
    
    async def perform_deep_analysis(self) -> Dict[str, Any]:
        """Perform deep market analysis for strategic planning."""
        try:
            logger.info("Performing deep market analysis")
            
            # Get comprehensive market data
            market_data = await self._gather_market_data()
            
            # Analyze multiple timeframes
            short_term_trends = self._analyze_trends(market_data)
            
            # Identify opportunities
            opportunities = await self.identify_earning_opportunities()
            
            # Generate strategic insights
            insights = {
                "market_summary": {
                    "current_conditions": market_data,
                    "trends": short_term_trends,
                    "opportunities_count": len(opportunities)
                },
                "recommendations": {
                    "immediate_actions": [opp for opp in opportunities if opp.time_sensitivity == "immediate"],
                    "strategic_actions": [opp for opp in opportunities if opp.time_sensitivity in ["short_term", "long_term"]]
                },
                "risk_assessment": {
                    "overall_risk": "low" if all(opp.risk_level == "low" for opp in opportunities) else "medium",
                    "market_volatility": short_term_trends["fee_trend"]
                }
            }
            
            logger.info("Deep analysis completed", opportunities=len(opportunities))
            return insights
            
        except Exception as e:
            logger.error("Failed to perform deep analysis", error=str(e))
            return {"error": str(e)}
    
    def update_historical_data(self, market_data: Dict[str, Any]) -> None:
        """Update historical data for trend analysis."""
        try:
            # Store fee data
            if "fee_estimates" in market_data:
                fee_record = {
                    "timestamp": market_data["timestamp"],
                    "6_block_fee": market_data["fee_estimates"].get("6_block", 0),
                    "1_block_fee": market_data["fee_estimates"].get("1_block", 0)
                }
                self.fee_history.append(fee_record)
                
                # Keep only last 100 records
                if len(self.fee_history) > 100:
                    self.fee_history = self.fee_history[-100:]
            
            # Store mempool data
            if "mempool_info" in market_data:
                mempool_record = {
                    "timestamp": market_data["timestamp"],
                    "height": market_data.get("blockchain_info", {}).get("blocks", 0),
                    "mempool_size": market_data["mempool_info"]["size"],
                    "mempool_usage": market_data["mempool_info"]["usage"]
                }
                self.mempool_history.append(mempool_record)
                
                # Keep only last 100 records
                if len(self.mempool_history) > 100:
                    self.mempool_history = self.mempool_history[-100:]
            
        except Exception as e:
            logger.error("Failed to update historical data", error=str(e))
    
    def close(self) -> None:
        """Close adapters and cleanup."""
        try:
            self.bitcoin_adapter.close()
            self.electrs_adapter.close()
        except Exception as e:
            logger.error("Failed to close market analyzer", error=str(e))
