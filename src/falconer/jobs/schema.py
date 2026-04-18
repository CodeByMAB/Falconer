"""Pydantic models for job requests, routing, execution, and history."""

from datetime import datetime
from typing import Any, Dict, Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, Field

JobCategory = Literal[
    "data_intelligence",
    "workflow_automation",
    "consulting",
    "agent_collaboration",
]

JobPriority = Literal["low", "standard", "high", "critical"]

JobState = Literal[
    "pending",
    "queued",
    "running",
    "completed",
    "failed",
    "cancelled",
]


class JobStatus(BaseModel):
    """Current lifecycle state of a job."""

    state: JobState = Field(default="pending", description="Lifecycle state")
    message: Optional[str] = Field(default=None, description="Human-readable status detail")
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }


class JobRequest(BaseModel):
    """Inbound job request from any channel (API, CLI, webhook, etc.)."""

    text: str = Field(description="Natural-language description of the work requested")
    channel: str = Field(default="unknown", description="Source channel identifier")
    category: Optional[JobCategory] = Field(
        default=None,
        description="If set, skip LLM classification for category",
    )
    priority: Optional[JobPriority] = Field(
        default=None,
        description="If set, skip LLM suggestion for priority",
    )
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Channel-specific context")
    client_ref: Optional[str] = Field(default=None, description="External correlation id")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }


class Job(BaseModel):
    """A classified, routable unit of work."""

    job_id: str = Field(default_factory=lambda: str(uuid4()))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    status: JobStatus = Field(default_factory=JobStatus)
    category: JobCategory = Field(description="Routed job category")
    priority: JobPriority = Field(default="standard", description="Execution priority")
    channel: str = Field(default="unknown")
    text: str = Field(description="Original request text")
    metadata: Dict[str, Any] = Field(default_factory=dict)
    client_ref: Optional[str] = None
    classification: Dict[str, Any] = Field(
        default_factory=dict,
        description="Raw LLM classification payload when used",
    )

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }


class JobResult(BaseModel):
    """Outcome of executing a job."""

    job_id: str
    success: bool
    category: JobCategory
    completed_at: datetime = Field(default_factory=datetime.utcnow)
    summary: str = Field(default="", description="Short human-readable outcome")
    data: Dict[str, Any] = Field(default_factory=dict, description="Structured executor output")
    error_message: Optional[str] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }


class JobSummary(BaseModel):
    """Lightweight job row for listings."""

    job_id: str
    created_at: datetime
    category: JobCategory
    priority: JobPriority
    state: JobState
    channel: str

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }
