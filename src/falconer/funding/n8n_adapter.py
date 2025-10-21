"""n8n adapter for sending funding proposals and handling webhook verification."""

import hashlib
import hmac
import time
from typing import Any, Dict, Optional

import httpx

from ..config import Config
from ..logging import get_logger
from .schema import FundingProposal

logger = get_logger(__name__)


class N8nAdapter:
    """Adapter for n8n webhook integration."""
    
    def __init__(self, config: Config):
        """Initialize the n8n adapter."""
        self.config = config
        self.webhook_url = config.n8n_webhook_url
        self.auth_token = config.n8n_webhook_auth_token
        self.secret = config.n8n_webhook_secret
        self.timeout = config.n8n_webhook_timeout_seconds
    
    async def send_proposal(self, proposal: FundingProposal) -> Dict[str, Any]:
        """Send funding proposal to n8n webhook."""
        if not self.webhook_url:
            raise ValueError("n8n webhook URL not configured")
        
        # Format proposal data for n8n
        payload = {
            "proposal_id": proposal.proposal_id,
            "requested_amount_sats": proposal.requested_amount_sats,
            "current_balance_sats": proposal.current_balance_sats,
            "justification": proposal.justification,
            "intended_use": proposal.intended_use,
            "expected_roi_sats": proposal.expected_roi_sats,
            "risk_assessment": proposal.risk_assessment,
            "strategies_to_execute": proposal.strategies_to_execute,
            "time_horizon_days": proposal.time_horizon_days,
            "created_at": proposal.created_at.isoformat(),
            "formatted_message": self.format_proposal_for_human(proposal),
        }
        
        # Prepare headers
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Falconer/1.0",
        }
        
        # Add authentication if configured
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                logger.info(
                    "Sending funding proposal to n8n",
                    extra={
                        "proposal_id": proposal.proposal_id,
                        "webhook_url": self.webhook_url,
                        "requested_amount_sats": proposal.requested_amount_sats,
                    }
                )
                
                response = await client.post(
                    self.webhook_url,
                    json=payload,
                    headers=headers,
                )
                
                response.raise_for_status()
                
                response_data = response.json() if response.content else {}
                
                logger.info(
                    "Successfully sent funding proposal to n8n",
                    extra={
                        "proposal_id": proposal.proposal_id,
                        "status_code": response.status_code,
                        "response_data": response_data,
                    }
                )
                
                return {
                    "success": True,
                    "status_code": response.status_code,
                    "workflow_id": response_data.get("workflow_id"),
                    "response_data": response_data,
                }
                
        except httpx.TimeoutException:
            logger.error(
                "Timeout sending funding proposal to n8n",
                extra={
                    "proposal_id": proposal.proposal_id,
                    "timeout_seconds": self.timeout,
                }
            )
            raise
        except httpx.HTTPStatusError as e:
            logger.error(
                "HTTP error sending funding proposal to n8n",
                extra={
                    "proposal_id": proposal.proposal_id,
                    "status_code": e.response.status_code,
                    "response_text": e.response.text,
                }
            )
            raise
        except Exception as e:
            logger.error(
                "Unexpected error sending funding proposal to n8n",
                extra={
                    "proposal_id": proposal.proposal_id,
                    "error": str(e),
                }
            )
            raise
    
    def verify_webhook_signature(self, payload: bytes, signature: str, timestamp: str) -> bool:
        """Verify HMAC-SHA256 signature from n8n approval webhook."""
        if not self.secret:
            if self.config.env == "prod":
                logger.error("No webhook secret configured in production environment")
                return False  # Require secret in production
            else:
                logger.warning("No webhook secret configured, skipping signature verification")
                return True  # Allow if no secret configured (dev mode)
        
        try:
            # Check timestamp is within acceptable window (±5 minutes)
            current_time = int(time.time())
            webhook_time = int(timestamp)
            time_diff = abs(current_time - webhook_time)
            
            if time_diff > 300:  # 5 minutes
                logger.warning(
                    "Webhook timestamp too old",
                    extra={
                        "timestamp": timestamp,
                        "current_time": current_time,
                        "time_diff_seconds": time_diff,
                    }
                )
                return False
            
            # Compute expected signature
            message = timestamp.encode() + payload
            expected_signature = hmac.new(
                self.secret.encode(),
                message,
                hashlib.sha256
            ).hexdigest()
            
            # Constant-time comparison
            is_valid = hmac.compare_digest(signature, expected_signature)
            
            if not is_valid:
                logger.warning(
                    "Invalid webhook signature",
                    extra={
                        "provided_signature": signature,
                        "expected_signature": expected_signature,
                    }
                )
            
            return is_valid
            
        except (ValueError, TypeError) as e:
            logger.error(
                "Error verifying webhook signature",
                extra={
                    "error": str(e),
                    "signature": signature,
                    "timestamp": timestamp,
                }
            )
            return False
    
    def format_proposal_for_human(self, proposal: FundingProposal) -> str:
        """Format proposal as human-readable text for n8n notification."""
        lines = [
            "🤖 FALCONER FUNDING REQUEST",
            "",
            f"💰 Amount Requested: {proposal.requested_amount_sats:,} sats",
            f"💳 Current Balance: {proposal.current_balance_sats:,} sats",
            f"📊 Expected ROI: {proposal.expected_roi_sats:,} sats",
            f"⏱️ Time Horizon: {proposal.time_horizon_days} days",
            f"⚠️ Risk Level: {proposal.risk_assessment.upper()}",
            "",
            "📝 JUSTIFICATION:",
            proposal.justification,
            "",
            "🎯 INTENDED USE:",
            proposal.intended_use,
            "",
            "🚀 STRATEGIES TO EXECUTE:",
        ]
        
        if proposal.strategies_to_execute:
            for strategy in proposal.strategies_to_execute:
                lines.append(f"  • {strategy}")
        else:
            lines.append("  • Market making")
            lines.append("  • Arbitrage opportunities")
            lines.append("  • Yield farming")
        
        lines.extend([
            "",
            f"🆔 Proposal ID: {proposal.proposal_id}",
            f"📅 Created: {proposal.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}",
            "",
            "Please approve or reject this funding request.",
        ])
        
        return "\n".join(lines)
