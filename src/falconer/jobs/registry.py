"""Service capability manifest for Falconer job routing and pricing."""

from typing import List, Optional

from pydantic import BaseModel, Field


class ServiceCapability(BaseModel):
    """One offered capability with pricing and endpoint metadata."""

    service_id: str = Field(description="Stable identifier")
    name: str = Field(description="Display name")
    category: str = Field(
        description="Job category key: data_intelligence, workflow_automation, etc."
    )
    description: str = Field(default="")
    base_price_sats: int = Field(ge=0, description="Listed base price in satoshis")
    endpoint: Optional[str] = Field(
        default=None,
        description="HTTP path, webhook id, or internal handler key",
    )
    tags: List[str] = Field(default_factory=list)


class ServiceRegistry(BaseModel):
    """Holds the capability manifest: services, pricing, and endpoints."""

    version: str = Field(default="1", description="Manifest schema version")
    services: List[ServiceCapability] = Field(default_factory=list)

    def by_category(self, category: str) -> List[ServiceCapability]:
        return [s for s in self.services if s.category == category]

    def by_id(self, service_id: str) -> Optional[ServiceCapability]:
        for s in self.services:
            if s.service_id == service_id:
                return s
        return None


def default_service_registry() -> ServiceRegistry:
    """Built-in manifest aligned with earning strategies and job categories."""
    return ServiceRegistry(
        services=[
            ServiceCapability(
                service_id="fee_intelligence",
                name="Fee intelligence",
                category="data_intelligence",
                description="Fee market reports and briefs",
                base_price_sats=1000,
                endpoint="internal:earning_strategy:fee_intelligence",
                tags=["bitcoin", "fees"],
            ),
            ServiceCapability(
                service_id="mempool_monitoring",
                name="Mempool monitoring",
                category="data_intelligence",
                description="Congestion and mempool alerts",
                base_price_sats=500,
                endpoint="internal:earning_strategy:mempool_monitoring",
                tags=["mempool"],
            ),
            ServiceCapability(
                service_id="n8n_workflow_dispatch",
                name="n8n workflow automation",
                category="workflow_automation",
                description="Dispatch work to n8n via webhook",
                base_price_sats=0,
                endpoint="webhook:n8n",
                tags=["n8n", "automation"],
            ),
            ServiceCapability(
                service_id="consulting_session",
                name="Consulting",
                category="consulting",
                description="Human-in-the-loop or advisory workflows",
                base_price_sats=0,
                endpoint="internal:consulting",
                tags=["consulting"],
            ),
            ServiceCapability(
                service_id="agent_subtask",
                name="Agent collaboration",
                category="agent_collaboration",
                description="Delegated sub-tasks across agents",
                base_price_sats=0,
                endpoint="internal:agent_subtask",
                tags=["agents"],
            ),
        ],
    )
