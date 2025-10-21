"""Funding proposal management for autonomous Bitcoin earning."""

from .manager import FundingProposalManager
from .n8n_adapter import N8nAdapter
from .schema import FundingProposal, ProposalApproval, ProposalSummary
from .webhook_server import create_webhook_app, run_webhook_server

__all__ = [
    "FundingProposalManager",
    "N8nAdapter", 
    "FundingProposal",
    "ProposalApproval",
    "ProposalSummary",
    "create_webhook_app",
    "run_webhook_server",
]
