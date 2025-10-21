"""Fee brief task - generates fee intelligence reports."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from ..adapters.bitcoind import BitcoinAdapter
from ..adapters.electrs import ElectrsAdapter
from ..config import Config
from ..logging import get_logger

logger = get_logger(__name__)


class FeeEstimate(BaseModel):
    """Fee estimate model."""

    target_blocks: int
    fee_rate_sats_per_vbyte: float
    confidence: Optional[float] = None


class MempoolStats(BaseModel):
    """Mempool statistics model."""

    size: int
    bytes: int
    usage: int
    maxmempool: int
    mempoolminfee: float
    minrelaytxfee: float


class FeeBrief(BaseModel):
    """Fee brief report model."""

    timestamp: datetime
    current_height: int
    fee_estimates: List[FeeEstimate]
    mempool_stats: MempoolStats
    recent_blocks: List[Dict[str, Any]]
    recommendations: Dict[str, Any]


class FeeBriefTask:
    """Task for generating fee intelligence briefs."""

    def __init__(
        self,
        config: Config,
        bitcoin_adapter: BitcoinAdapter,
        electrs_adapter: ElectrsAdapter,
    ):
        """Initialize fee brief task.

        Args:
            config: Falconer configuration
            bitcoin_adapter: Bitcoin Core adapter
            electrs_adapter: Electrs adapter
        """
        self.config = config
        self.bitcoin_adapter = bitcoin_adapter
        self.electrs_adapter = electrs_adapter

    def generate_fee_brief(self) -> FeeBrief:
        """Generate a comprehensive fee intelligence brief.

        Returns:
            Fee brief report
        """
        logger.info("Generating fee brief")

        try:
            # Get current blockchain info
            blockchain_info = self.bitcoin_adapter.get_blockchain_info()
            current_height = blockchain_info["blocks"]

            # Get fee estimates for different confirmation targets
            fee_estimates = []
            targets = [1, 3, 6, 12, 24, 72, 144]

            for target in targets:
                try:
                    estimate = self.bitcoin_adapter.estimate_smart_fee(target)
                    if "feerate" in estimate:
                        fee_estimates.append(
                            FeeEstimate(
                                target_blocks=target,
                                fee_rate_sats_per_vbyte=estimate["feerate"]
                                * 100000,  # Convert to sats/vbyte
                                confidence=estimate.get("blocks", None),
                            )
                        )
                except Exception as e:
                    logger.warning(
                        f"Failed to get fee estimate for {target} blocks", error=str(e)
                    )

            # Get mempool statistics
            mempool_info = self.bitcoin_adapter.get_mempool_info()
            mempool_stats = MempoolStats(
                size=mempool_info["size"],
                bytes=mempool_info["bytes"],
                usage=mempool_info["usage"],
                maxmempool=mempool_info["maxmempool"],
                mempoolminfee=mempool_info["mempoolminfee"],
                minrelaytxfee=mempool_info["minrelaytxfee"],
            )

            # Get recent blocks information
            recent_blocks = self._get_recent_blocks(current_height, 5)

            # Generate recommendations
            recommendations = self._generate_recommendations(
                fee_estimates, mempool_stats
            )

            brief = FeeBrief(
                timestamp=datetime.utcnow(),
                current_height=current_height,
                fee_estimates=fee_estimates,
                mempool_stats=mempool_stats,
                recent_blocks=recent_blocks,
                recommendations=recommendations,
            )

            logger.info(
                "Fee brief generated successfully",
                height=current_height,
                mempool_size=mempool_stats.size,
                estimates_count=len(fee_estimates),
            )

            return brief

        except Exception as e:
            logger.error("Failed to generate fee brief", error=str(e))
            raise

    def _get_recent_blocks(
        self, current_height: int, count: int
    ) -> List[Dict[str, Any]]:
        """Get information about recent blocks.

        Args:
            current_height: Current blockchain height
            count: Number of recent blocks to analyze

        Returns:
            List of recent block information
        """
        recent_blocks = []

        try:
            # Get recent block hashes
            for i in range(count):
                height = current_height - i
                if height < 0:
                    break

                try:
                    block_hash = self.bitcoin_adapter._make_rpc_call(
                        "getblockhash", [height]
                    )
                    block_info = self.bitcoin_adapter._make_rpc_call(
                        "getblock", [block_hash.result]
                    )

                    recent_blocks.append(
                        {
                            "height": height,
                            "hash": block_hash.result,
                            "time": block_info.result["time"],
                            "size": block_info.result["size"],
                            "tx_count": len(block_info.result["tx"]),
                            "fee_total": block_info.result.get("fee_total", 0),
                        }
                    )
                except Exception as e:
                    logger.warning(f"Failed to get block {height}", error=str(e))
                    continue

        except Exception as e:
            logger.warning("Failed to get recent blocks", error=str(e))

        return recent_blocks

    def _generate_recommendations(
        self, fee_estimates: List[FeeEstimate], mempool_stats: MempoolStats
    ) -> Dict[str, Any]:
        """Generate fee recommendations based on current conditions.

        Args:
            fee_estimates: Current fee estimates
            mempool_stats: Mempool statistics

        Returns:
            Recommendations dictionary
        """
        recommendations = {
            "urgency": "normal",
            "recommended_fee_rate": 10.0,
            "reasoning": [],
            "market_conditions": "normal",
        }

        if not fee_estimates:
            recommendations["reasoning"].append("No fee estimates available")
            return recommendations

        # Find the 6-block estimate (standard confirmation target)
        six_block_estimate = None
        for estimate in fee_estimates:
            if estimate.target_blocks == 6:
                six_block_estimate = estimate
                break

        if six_block_estimate:
            recommendations["recommended_fee_rate"] = (
                six_block_estimate.fee_rate_sats_per_vbyte
            )

            # Determine urgency based on fee rate
            if six_block_estimate.fee_rate_sats_per_vbyte > 50:
                recommendations["urgency"] = "high"
                recommendations["market_conditions"] = "congested"
                recommendations["reasoning"].append(
                    "High fee rates indicate network congestion"
                )
            elif six_block_estimate.fee_rate_sats_per_vbyte > 20:
                recommendations["urgency"] = "medium"
                recommendations["market_conditions"] = "busy"
                recommendations["reasoning"].append(
                    "Moderate fee rates suggest increased activity"
                )
            else:
                recommendations["urgency"] = "low"
                recommendations["market_conditions"] = "normal"
                recommendations["reasoning"].append(
                    "Low fee rates indicate normal network conditions"
                )

        # Analyze mempool conditions
        mempool_usage_percent = (mempool_stats.usage / mempool_stats.maxmempool) * 100
        if mempool_usage_percent > 80:
            recommendations["urgency"] = "high"
            recommendations["reasoning"].append("Mempool is nearly full")
        elif mempool_usage_percent > 60:
            if recommendations["urgency"] == "low":
                recommendations["urgency"] = "medium"
            recommendations["reasoning"].append("Mempool usage is elevated")

        # Add general recommendations
        if recommendations["urgency"] == "high":
            recommendations["reasoning"].append(
                "Consider waiting or using higher fee rates"
            )
        elif recommendations["urgency"] == "low":
            recommendations["reasoning"].append(
                "Good time for transactions with standard fees"
            )

        return recommendations

    def save_fee_brief(self, brief: FeeBrief, filename: Optional[str] = None) -> str:
        """Save fee brief to file.

        Args:
            brief: Fee brief to save
            filename: Optional filename (defaults to timestamp-based name)

        Returns:
            Saved filename
        """
        if filename is None:
            timestamp = brief.timestamp.strftime("%Y%m%d_%H%M%S")
            filename = f"fee_brief_{timestamp}.json"

        try:
            with open(filename, "w") as f:
                f.write(brief.json(indent=2))

            logger.info("Fee brief saved", filename=filename)
            return filename

        except Exception as e:
            logger.error("Failed to save fee brief", filename=filename, error=str(e))
            raise
