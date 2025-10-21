"""FastAPI-based webhook server for receiving approval notifications from n8n."""

import json
from typing import Dict, Any

from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import JSONResponse
import uvicorn

from ..config import Config
from ..logging import get_logger
from .manager import FundingProposalManager
from .n8n_adapter import N8nAdapter
from .schema import ProposalApproval

logger = get_logger(__name__)


def create_webhook_app(
    config: Config,
    proposal_manager: FundingProposalManager,
    n8n_adapter: N8nAdapter,
) -> FastAPI:
    """Factory function to create configured FastAPI app with dependency injection."""
    
    app = FastAPI(
        title="Falconer Webhook Server",
        description="Webhook server for receiving funding proposal approvals from n8n",
        version="1.0.0",
    )
    
    # Store dependencies in app state
    app.state.config = config
    app.state.proposal_manager = proposal_manager
    app.state.n8n_adapter = n8n_adapter
    
    @app.post("/webhook/approval")
    async def receive_approval(request: Request):
        """Main endpoint to receive approval notifications from n8n."""
        try:
            # Get dependencies from app state
            config = app.state.config
            proposal_manager = app.state.proposal_manager
            n8n_adapter = app.state.n8n_adapter
            
            # Extract signature and timestamp from headers
            signature = request.headers.get("X-Signature")
            timestamp = request.headers.get("X-Timestamp")
            
            if not signature or not timestamp:
                logger.warning("Missing signature or timestamp in webhook request")
                raise HTTPException(status_code=401, detail="Missing authentication headers")
            
            # Get raw body for signature verification
            body = await request.body()
            
            # Verify signature
            if not n8n_adapter.verify_webhook_signature(body, signature, timestamp):
                logger.warning("Invalid webhook signature")
                raise HTTPException(status_code=401, detail="Invalid signature")
            
            # Parse approval data
            try:
                approval_data = json.loads(body.decode())
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in webhook payload: {e}")
                raise HTTPException(status_code=400, detail="Invalid JSON payload")
            
            proposal_id = approval_data.get("proposal_id")
            status = approval_data.get("status")
            approved_by = approval_data.get("approved_by", "unknown")
            approval_notes = approval_data.get("approval_notes")
            
            if not proposal_id or not status:
                logger.warning("Missing required fields in approval data")
                raise HTTPException(status_code=400, detail="Missing proposal_id or status")
            
            if status not in ["approved", "rejected"]:
                logger.warning(f"Invalid status in approval data: {status}")
                raise HTTPException(status_code=400, detail="Status must be 'approved' or 'rejected'")
            
            # Load proposal
            proposal = proposal_manager.get_proposal(proposal_id)
            if not proposal:
                logger.warning(f"Proposal not found: {proposal_id}")
                raise HTTPException(status_code=404, detail="Proposal not found")
            
            if proposal.status != "pending":
                logger.warning(f"Proposal not in pending status: {proposal_id} (status: {proposal.status})")
                raise HTTPException(status_code=400, detail=f"Proposal not in pending status (current: {proposal.status})")
            
            # Process approval/rejection
            if status == "approved":
                updated_proposal = proposal_manager.approve_proposal(proposal_id, approved_by, approval_notes)
                logger.info(
                    "Proposal approved via webhook",
                    extra={
                        "proposal_id": proposal_id,
                        "approved_by": approved_by,
                        "requested_amount_sats": updated_proposal.requested_amount_sats,
                    }
                )
                
                # Initiate human handoff for PSBT creation
                try:
                    # Log explicit instruction for operator
                    logger.info(
                        "FUNDING PROPOSAL APPROVED - HUMAN HANDOFF REQUIRED",
                        extra={
                            "proposal_id": proposal_id,
                            "requested_amount_sats": updated_proposal.requested_amount_sats,
                            "action_required": "Create and broadcast PSBT for approved funding",
                            "cli_command": f"falconer funding execute --proposal-id {proposal_id}",
                        }
                    )
                    
                    # Persist a flag for CLI consumption
                    # This could be extended to create a dedicated task queue
                    approval_record = {
                        "proposal_id": proposal_id,
                        "approved_at": updated_proposal.approved_at.isoformat(),
                        "approved_by": approved_by,
                        "requested_amount_sats": updated_proposal.requested_amount_sats,
                        "status": "pending_execution",
                        "action_required": "create_psbt",
                    }
                    
                    # Store in persistence for CLI to consume
                    # This is a simple approach - in production you might use a proper task queue
                    import json
                    import os
                    from pathlib import Path
                    
                    approval_queue_dir = Path("data/approval_queue")
                    approval_queue_dir.mkdir(parents=True, exist_ok=True)
                    
                    approval_file = approval_queue_dir / f"{proposal_id}.json"
                    with open(approval_file, "w") as f:
                        json.dump(approval_record, f, indent=2)
                    
                    logger.info(
                        "Approval record persisted for CLI consumption",
                        extra={
                            "proposal_id": proposal_id,
                            "approval_file": str(approval_file),
                        }
                    )
                    
                except Exception as e:
                    logger.error(
                        "Failed to initiate human handoff after approval",
                        extra={
                            "proposal_id": proposal_id,
                            "error": str(e),
                        }
                    )
            else:  # rejected
                reason = approval_notes or "Rejected via webhook"
                updated_proposal = proposal_manager.reject_proposal(proposal_id, approved_by, reason)
                logger.info(
                    "Proposal rejected via webhook",
                    extra={
                        "proposal_id": proposal_id,
                        "rejected_by": approved_by,
                        "reason": reason,
                    }
                )
            
            return JSONResponse(
                status_code=200,
                content={
                    "success": True,
                    "message": f"Proposal {status} successfully",
                    "proposal_id": proposal_id,
                    "status": updated_proposal.status,
                    "updated_at": updated_proposal.approved_at.isoformat() if updated_proposal.approved_at else updated_proposal.rejected_at.isoformat() if updated_proposal.rejected_at else None,
                }
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error processing webhook approval: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    @app.get("/webhook/health")
    async def health_check():
        """Health check endpoint."""
        return {
            "status": "healthy",
            "service": "falconer-webhook",
            "version": "1.0.0",
        }
    
    @app.get("/webhook/proposals/{proposal_id}")
    async def get_proposal_status(proposal_id: str):
        """Query endpoint to check proposal status."""
        proposal_manager = app.state.proposal_manager
        
        proposal = proposal_manager.get_proposal(proposal_id)
        if not proposal:
            raise HTTPException(status_code=404, detail="Proposal not found")
        
        return {
            "proposal_id": proposal.proposal_id,
            "status": proposal.status,
            "created_at": proposal.created_at.isoformat(),
            "requested_amount_sats": proposal.requested_amount_sats,
            "approved_at": proposal.approved_at.isoformat() if proposal.approved_at else None,
            "approved_by": proposal.approved_by,
            "executed_at": proposal.executed_at.isoformat() if proposal.executed_at else None,
            "execution_txid": proposal.execution_txid,
        }
    
    return app


def run_webhook_server(
    config: Config,
    proposal_manager: FundingProposalManager,
    n8n_adapter: N8nAdapter,
):
    """Start uvicorn server with host and port from config."""
    
    app = create_webhook_app(config, proposal_manager, n8n_adapter)
    
    logger.info(
        "Starting webhook server",
        extra={
            "host": config.webhook_server_host,
            "port": config.webhook_server_port,
            "reload": config.webhook_server_reload,
        }
    )
    
    uvicorn.run(
        app,
        host=config.webhook_server_host,
        port=config.webhook_server_port,
        reload=config.webhook_server_reload,
        log_level="info",
    )
