"""AI-driven earning strategies for autonomous Bitcoin earning."""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from ..adapters.lnbits import LNbitsAdapter
from ..config import Config
from ..logging import get_logger
from ..tasks.fee_brief import FeeBriefTask
from ..adapters.bitcoind import BitcoinAdapter
from ..adapters.electrs import ElectrsAdapter

logger = get_logger(__name__)


class EarningStrategy(BaseModel):
    """Base earning strategy model."""
    
    name: str
    description: str
    base_price_sats: int
    min_price_sats: int
    max_price_sats: int
    risk_level: str  # "low", "medium", "high"
    time_to_complete_minutes: int
    requirements: List[str]
    success_rate: float  # Historical success rate
    last_used: Optional[datetime] = None
    total_earnings: int = 0
    total_uses: int = 0


class StrategyExecution(BaseModel):
    """Strategy execution result."""
    
    strategy_name: str
    execution_time: datetime
    price_charged_sats: int
    success: bool
    earnings_sats: int
    error_message: Optional[str] = None
    execution_time_seconds: float


class EarningStrategyManager:
    """Manages AI-driven earning strategies and their execution."""
    
    def __init__(self, config: Config):
        """Initialize the earning strategy manager.
        
        Args:
            config: Falconer configuration
        """
        self.config = config
        self.lnbits_adapter = LNbitsAdapter(config)
        self.bitcoin_adapter = BitcoinAdapter(config)
        self.electrs_adapter = ElectrsAdapter(config)
        
        # Initialize strategies
        self.strategies = self._initialize_strategies()
        self.execution_history: List[StrategyExecution] = []
        
        logger.info("Earning Strategy Manager initialized", strategies_count=len(self.strategies))
    
    def _initialize_strategies(self) -> Dict[str, EarningStrategy]:
        """Initialize available earning strategies."""
        strategies = {}
        
        # Fee Intelligence Strategy
        strategies["fee_intelligence"] = EarningStrategy(
            name="fee_intelligence",
            description="Generate comprehensive fee intelligence reports with market analysis",
            base_price_sats=1000,  # 10k sats base price
            min_price_sats=500,    # 5k sats minimum
            max_price_sats=5000,   # 50k sats maximum
            risk_level="low",
            time_to_complete_minutes=2,
            requirements=["bitcoin_core", "electrs", "mempool_data"],
            success_rate=0.95
        )
        
        # Mempool Monitoring Strategy
        strategies["mempool_monitoring"] = EarningStrategy(
            name="mempool_monitoring",
            description="Provide real-time mempool monitoring and congestion alerts",
            base_price_sats=500,   # 5k sats base price
            min_price_sats=200,    # 2k sats minimum
            max_price_sats=2000,   # 20k sats maximum
            risk_level="low",
            time_to_complete_minutes=1,
            requirements=["mempool_data", "real_time_updates"],
            success_rate=0.98
        )
        
        # Transaction Optimization Strategy
        strategies["transaction_optimization"] = EarningStrategy(
            name="transaction_optimization",
            description="Optimize transaction timing and fee rates for maximum efficiency",
            base_price_sats=800,   # 8k sats base price
            min_price_sats=400,    # 4k sats minimum
            max_price_sats=3000,   # 30k sats maximum
            risk_level="medium",
            time_to_complete_minutes=3,
            requirements=["fee_estimation", "timing_analysis", "utxo_analysis"],
            success_rate=0.85
        )
        
        # Market Analysis Strategy
        strategies["market_analysis"] = EarningStrategy(
            name="market_analysis",
            description="Provide deep market analysis and trend predictions",
            base_price_sats=1500,  # 15k sats base price
            min_price_sats=750,    # 7.5k sats minimum
            max_price_sats=6000,   # 60k sats maximum
            risk_level="medium",
            time_to_complete_minutes=5,
            requirements=["historical_data", "trend_analysis", "prediction_models"],
            success_rate=0.75
        )
        
        # Lightning Network Services Strategy
        strategies["lightning_services"] = EarningStrategy(
            name="lightning_services",
            description="Provide Lightning Network routing and payment services",
            base_price_sats=200,   # 2k sats base price
            min_price_sats=100,    # 1k sats minimum
            max_price_sats=1000,   # 10k sats maximum
            risk_level="low",
            time_to_complete_minutes=1,
            requirements=["lightning_node", "routing_capacity"],
            success_rate=0.90
        )
        
        return strategies
    
    def get_available_strategies(self) -> List[Dict[str, Any]]:
        """Get list of available strategies with current pricing."""
        available = []
        
        for strategy in self.strategies.values():
            # Calculate dynamic pricing based on market conditions
            current_price = self._calculate_dynamic_price(strategy)
            
            available.append({
                "name": strategy.name,
                "description": strategy.description,
                "current_price_sats": current_price,
                "min_price_sats": strategy.min_price_sats,
                "max_price_sats": strategy.max_price_sats,
                "risk_level": strategy.risk_level,
                "time_to_complete_minutes": strategy.time_to_complete_minutes,
                "success_rate": strategy.success_rate,
                "total_earnings": strategy.total_earnings,
                "total_uses": strategy.total_uses
            })
        
        return available
    
    def _calculate_dynamic_price(self, strategy: EarningStrategy) -> int:
        """Calculate dynamic pricing based on market conditions and demand."""
        base_price = strategy.base_price_sats
        
        # Adjust based on recent success rate
        if strategy.success_rate > 0.9:
            price_multiplier = 1.2  # 20% premium for high success rate
        elif strategy.success_rate > 0.8:
            price_multiplier = 1.1  # 10% premium
        elif strategy.success_rate < 0.7:
            price_multiplier = 0.8  # 20% discount for lower success rate
        else:
            price_multiplier = 1.0  # Base price
        
        # Adjust based on recent usage (scarcity pricing)
        if strategy.last_used:
            time_since_last_use = datetime.utcnow() - strategy.last_used
            if time_since_last_use < timedelta(hours=1):
                price_multiplier *= 1.1  # 10% premium for high demand
            elif time_since_last_use > timedelta(days=1):
                price_multiplier *= 0.9  # 10% discount for low demand
        
        # Calculate final price
        final_price = int(base_price * price_multiplier)
        
        # Ensure price is within bounds
        final_price = max(strategy.min_price_sats, min(strategy.max_price_sats, final_price))
        
        return final_price
    
    async def execute_strategy(self, strategy_name: str, parameters: Dict[str, Any]) -> StrategyExecution:
        """Execute a specific earning strategy."""
        start_time = datetime.utcnow()
        
        try:
            if strategy_name not in self.strategies:
                raise ValueError(f"Unknown strategy: {strategy_name}")
            
            strategy = self.strategies[strategy_name]
            logger.info("Executing earning strategy", strategy=strategy_name, parameters=parameters)
            
            # Calculate dynamic price
            price = self._calculate_dynamic_price(strategy)
            
            # Execute the strategy
            result = await self._execute_strategy_implementation(strategy_name, parameters, price)
            
            # Create execution record
            execution = StrategyExecution(
                strategy_name=strategy_name,
                execution_time=start_time,
                price_charged_sats=price,
                success=result["success"],
                earnings_sats=result["earnings_sats"],
                error_message=result.get("error_message"),
                execution_time_seconds=(datetime.utcnow() - start_time).total_seconds()
            )
            
            # Update strategy statistics
            strategy.last_used = start_time
            strategy.total_uses += 1
            if result["success"]:
                strategy.total_earnings += result["earnings_sats"]
                # Update success rate
                successful_executions = sum(1 for e in self.execution_history if e.strategy_name == strategy_name and e.success)
                strategy.success_rate = successful_executions / strategy.total_uses
            
            # Store execution history
            self.execution_history.append(execution)
            
            logger.info("Strategy execution completed", 
                       strategy=strategy_name, 
                       success=result["success"],
                       earnings=result["earnings_sats"])
            
            return execution
            
        except Exception as e:
            logger.error("Strategy execution failed", strategy=strategy_name, error=str(e))
            
            execution = StrategyExecution(
                strategy_name=strategy_name,
                execution_time=start_time,
                price_charged_sats=0,
                success=False,
                earnings_sats=0,
                error_message=str(e),
                execution_time_seconds=(datetime.utcnow() - start_time).total_seconds()
            )
            
            self.execution_history.append(execution)
            return execution
    
    async def _execute_strategy_implementation(self, strategy_name: str, parameters: Dict[str, Any], price: int) -> Dict[str, Any]:
        """Execute the actual strategy implementation."""
        try:
            if strategy_name == "fee_intelligence":
                return await self._execute_fee_intelligence(parameters, price)
            elif strategy_name == "mempool_monitoring":
                return await self._execute_mempool_monitoring(parameters, price)
            elif strategy_name == "transaction_optimization":
                return await self._execute_transaction_optimization(parameters, price)
            elif strategy_name == "market_analysis":
                return await self._execute_market_analysis(parameters, price)
            elif strategy_name == "lightning_services":
                return await self._execute_lightning_services(parameters, price)
            else:
                raise ValueError(f"No implementation for strategy: {strategy_name}")
                
        except Exception as e:
            return {
                "success": False,
                "earnings_sats": 0,
                "error_message": str(e)
            }
    
    async def _execute_fee_intelligence(self, parameters: Dict[str, Any], price: int) -> Dict[str, Any]:
        """Execute fee intelligence strategy."""
        try:
            # Create fee brief task
            fee_task = FeeBriefTask(self.config, self.bitcoin_adapter, self.electrs_adapter)
            
            # Generate fee brief
            brief = fee_task.generate_fee_brief()
            
            # Create Lightning invoice for the service
            invoice = self.lnbits_adapter.create_invoice(
                amount=price,
                description=f"Fee Intelligence Report - {brief.timestamp.isoformat()}"
            )
            
            # In a real implementation, you would:
            # 1. Store the brief data
            # 2. Provide it to the customer
            # 3. Wait for payment
            # 4. Return the brief once paid
            
            logger.info("Fee intelligence service created", 
                       invoice_id=invoice.payment_hash,
                       price=price)
            
            return {
                "success": True,
                "earnings_sats": price,
                "service_data": {
                    "invoice": invoice.dict(),
                    "brief_summary": {
                        "timestamp": brief.timestamp.isoformat(),
                        "current_height": brief.current_height,
                        "recommendations": brief.recommendations
                    }
                }
            }
            
        except Exception as e:
            logger.error("Fee intelligence execution failed", error=str(e))
            return {
                "success": False,
                "earnings_sats": 0,
                "error_message": str(e)
            }
    
    async def _execute_mempool_monitoring(self, parameters: Dict[str, Any], price: int) -> Dict[str, Any]:
        """Execute mempool monitoring strategy."""
        try:
            # Get current mempool data
            mempool_info = self.bitcoin_adapter.get_mempool_info()
            
            # Create monitoring service
            invoice = self.lnbits_adapter.create_invoice(
                amount=price,
                description=f"Mempool Monitoring - {datetime.utcnow().isoformat()}"
            )
            
            # Provide mempool insights
            congestion_level = "low"
            usage_percent = (mempool_info["usage"] / mempool_info["maxmempool"]) * 100
            
            if usage_percent > 80:
                congestion_level = "critical"
            elif usage_percent > 60:
                congestion_level = "high"
            elif usage_percent > 30:
                congestion_level = "medium"
            
            return {
                "success": True,
                "earnings_sats": price,
                "service_data": {
                    "invoice": invoice.dict(),
                    "mempool_status": {
                        "congestion_level": congestion_level,
                        "usage_percent": usage_percent,
                        "size": mempool_info["size"],
                        "bytes": mempool_info["bytes"]
                    }
                }
            }
            
        except Exception as e:
            logger.error("Mempool monitoring execution failed", error=str(e))
            return {
                "success": False,
                "earnings_sats": 0,
                "error_message": str(e)
            }
    
    async def _execute_transaction_optimization(self, parameters: Dict[str, Any], price: int) -> Dict[str, Any]:
        """Execute transaction optimization strategy."""
        try:
            # Get fee estimates for optimization
            fee_estimates = {}
            for target in [1, 3, 6, 12, 24]:
                try:
                    estimate = self.bitcoin_adapter.estimate_smart_fee(target)
                    if "feerate" in estimate:
                        fee_estimates[f"{target}_block"] = estimate["feerate"] * 100000
                except Exception:
                    continue
            
            # Create optimization service
            invoice = self.lnbits_adapter.create_invoice(
                amount=price,
                description=f"Transaction Optimization - {datetime.utcnow().isoformat()}"
            )
            
            # Provide optimization recommendations
            recommendations = {
                "optimal_fee_rate": fee_estimates.get("6_block", 10),
                "urgent_fee_rate": fee_estimates.get("1_block", 20),
                "economical_fee_rate": fee_estimates.get("24_block", 5),
                "timing_recommendation": "optimal" if fee_estimates.get("6_block", 10) < 15 else "wait"
            }
            
            return {
                "success": True,
                "earnings_sats": price,
                "service_data": {
                    "invoice": invoice.dict(),
                    "optimization": recommendations
                }
            }
            
        except Exception as e:
            logger.error("Transaction optimization execution failed", error=str(e))
            return {
                "success": False,
                "earnings_sats": 0,
                "error_message": str(e)
            }
    
    async def _execute_market_analysis(self, parameters: Dict[str, Any], price: int) -> Dict[str, Any]:
        """Execute market analysis strategy."""
        try:
            # Perform comprehensive market analysis
            blockchain_info = self.bitcoin_adapter.get_blockchain_info()
            mempool_info = self.bitcoin_adapter.get_mempool_info()
            
            # Create market analysis service
            invoice = self.lnbits_adapter.create_invoice(
                amount=price,
                description=f"Market Analysis - {datetime.utcnow().isoformat()}"
            )
            
            # Generate market insights
            analysis = {
                "network_health": "good" if blockchain_info["blocks"] > 0 else "unknown",
                "mempool_congestion": "high" if mempool_info["usage"] > mempool_info["maxmempool"] * 0.8 else "normal",
                "recommendations": [
                    "Monitor fee trends closely",
                    "Consider batching transactions",
                    "Use replace-by-fee for urgent transactions"
                ]
            }
            
            return {
                "success": True,
                "earnings_sats": price,
                "service_data": {
                    "invoice": invoice.dict(),
                    "analysis": analysis
                }
            }
            
        except Exception as e:
            logger.error("Market analysis execution failed", error=str(e))
            return {
                "success": False,
                "earnings_sats": 0,
                "error_message": str(e)
            }
    
    async def _execute_lightning_services(self, parameters: Dict[str, Any], price: int) -> Dict[str, Any]:
        """Execute Lightning Network services strategy."""
        try:
            # Get Lightning wallet balance
            wallet_balance = self.lnbits_adapter.get_wallet_balance()
            
            # Create Lightning service
            invoice = self.lnbits_adapter.create_invoice(
                amount=price,
                description=f"Lightning Service - {datetime.utcnow().isoformat()}"
            )
            
            return {
                "success": True,
                "earnings_sats": price,
                "service_data": {
                    "invoice": invoice.dict(),
                    "lightning_status": {
                        "wallet_balance": wallet_balance.get("balance", 0),
                        "service_available": True
                    }
                }
            }
            
        except Exception as e:
            logger.error("Lightning services execution failed", error=str(e))
            return {
                "success": False,
                "earnings_sats": 0,
                "error_message": str(e)
            }
    
    async def adjust_pricing(self, strategy_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Adjust pricing for a strategy based on market conditions."""
        try:
            if strategy_name not in self.strategies:
                raise ValueError(f"Unknown strategy: {strategy_name}")
            
            strategy = self.strategies[strategy_name]
            
            # Calculate new pricing based on parameters
            adjustment_factor = parameters.get("adjustment_factor", 1.0)
            new_base_price = int(strategy.base_price_sats * adjustment_factor)
            
            # Update strategy pricing
            strategy.base_price_sats = max(strategy.min_price_sats, min(strategy.max_price_sats, new_base_price))
            
            logger.info("Pricing adjusted", 
                       strategy=strategy_name, 
                       new_base_price=strategy.base_price_sats,
                       adjustment_factor=adjustment_factor)
            
            return {
                "success": True,
                "new_base_price_sats": strategy.base_price_sats,
                "adjustment_factor": adjustment_factor
            }
            
        except Exception as e:
            logger.error("Pricing adjustment failed", strategy=strategy_name, error=str(e))
            return {
                "success": False,
                "error_message": str(e)
            }
    
    def get_strategy_performance(self, strategy_name: Optional[str] = None) -> Dict[str, Any]:
        """Get performance metrics for strategies."""
        if strategy_name:
            if strategy_name not in self.strategies:
                return {"error": f"Unknown strategy: {strategy_name}"}
            
            strategy = self.strategies[strategy_name]
            executions = [e for e in self.execution_history if e.strategy_name == strategy_name]
            
            return {
                "strategy_name": strategy_name,
                "total_earnings": strategy.total_earnings,
                "total_uses": strategy.total_uses,
                "success_rate": strategy.success_rate,
                "recent_executions": len([e for e in executions if e.execution_time > datetime.utcnow() - timedelta(days=7)]),
                "average_earnings_per_use": strategy.total_earnings / strategy.total_uses if strategy.total_uses > 0 else 0
            }
        else:
            # Return performance for all strategies
            performance = {}
            for name in self.strategies.keys():
                performance[name] = self.get_strategy_performance(name)
            return performance
    
    def close(self) -> None:
        """Close adapters and cleanup."""
        try:
            self.lnbits_adapter.close()
            self.bitcoin_adapter.close()
            self.electrs_adapter.close()
        except Exception as e:
            logger.error("Failed to close earning strategy manager", error=str(e))
