"""Pydantic models for funding proposals."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class FundingProposal(BaseModel):
    """Main funding proposal model."""
    
    proposal_id: str = Field(default_factory=lambda: str(uuid4()))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    status: str = Field(default="pending")  # pending, approved, rejected, executed, expired
    requested_amount_sats: int = Field(gt=0, description="Amount of Bitcoin requested in satoshis")
    current_balance_sats: int = Field(ge=0, description="Current wallet balance at time of proposal")
    justification: str = Field(description="AI-generated explanation for why funds are needed")
    intended_use: str = Field(description="Detailed plan for how funds will be used to earn more Bitcoin")
    expected_roi_sats: int = Field(ge=0, description="Expected return on investment in satoshis")
    risk_assessment: str = Field(default="medium", description="Risk level: low, medium, high")
    strategies_to_execute: List[str] = Field(default_factory=list, description="List of earning strategies planned")
    time_horizon_days: int = Field(gt=0, description="Expected timeframe for ROI in days")
    approved_at: Optional[datetime] = None
    approved_by: Optional[str] = None
    rejected_at: Optional[datetime] = None
    rejected_by: Optional[str] = None
    approval_notes: Optional[str] = None
    executed_at: Optional[datetime] = None
    execution_txid: Optional[str] = None
    n8n_workflow_id: Optional[str] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v),
        }


class ProposalApproval(BaseModel):
    """Model for approval notifications from n8n."""
    
    proposal_id: str = Field(description="ID of proposal being approved/rejected")
    status: str = Field(description="approved or rejected")
    approved_by: str = Field(description="Human identifier")
    approval_notes: Optional[str] = Field(default=None, description="Human comments")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    signature: str = Field(description="HMAC signature for verification")


class ProposalSummary(BaseModel):
    """Lightweight model for listing proposals."""
    
    proposal_id: str
    created_at: datetime
    status: str
    requested_amount_sats: int
    justification: str = Field(description="Truncated to 200 chars")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }
