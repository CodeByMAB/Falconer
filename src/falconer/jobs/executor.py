"""Job execution orchestration by category."""

from datetime import datetime
from typing import Any, Dict, Optional, TYPE_CHECKING

import httpx

from ..config import Config
from ..logging import get_logger
from .registry import ServiceRegistry, default_service_registry
from .schema import Job, JobCategory, JobPriority, JobResult, JobStatus

if TYPE_CHECKING:
    from ..ai.earning_strategies import EarningStrategyManager

logger = get_logger(__name__)


class N8nWorkflowComposer:
    """Compose and dispatch workflow automation jobs to n8n (webhook POST)."""

    def __init__(self, config: Config):
        self.config = config
        self.webhook_url = config.n8n_webhook_url
        self.auth_token = config.n8n_webhook_auth_token
        self.timeout = float(config.n8n_webhook_timeout_seconds)

    async def dispatch(self, job: Job) -> Dict[str, Any]:
        if not self.webhook_url:
            return {
                "success": False,
                "error": "n8n_webhook_url not configured",
            }
        payload = {
            "event": "falconer_job",
            "job_id": job.job_id,
            "category": job.category,
            "priority": job.priority,
            "text": job.text,
            "metadata": job.metadata,
            "workflow_hint": job.metadata.get("workflow_hint"),
        }
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Falconer-Jobs/1.0",
        }
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(self.webhook_url, json=payload, headers=headers)
                resp.raise_for_status()
                body = resp.json() if resp.content else {}
            return {"success": True, "status_code": resp.status_code, "response": body}
        except Exception as e:
            logger.error("n8n job dispatch failed", job_id=job.job_id, error=str(e))
            return {"success": False, "error": str(e)}


class ConsultingJobHandler:
    """Advisory / consulting category — structured handoff for human or policy review."""

    async def handle(self, job: Job) -> Dict[str, Any]:
        queue = job.metadata.get("consulting_queue", "default")
        logger.info("Consulting job recorded", job_id=job.job_id, queue=queue)
        return {
            "success": True,
            "queue": queue,
            "handoff": "pending_review",
            "notes": job.metadata.get("notes"),
        }


class SubTaskHandler:
    """Agent collaboration — delegate sub-tasks (placeholder for multi-agent orchestration)."""

    async def handle(self, job: Job) -> Dict[str, Any]:
        parent_ref = job.metadata.get("parent_job_id")
        subtasks = job.metadata.get("subtasks", [])
        logger.info(
            "Sub-task collaboration job",
            job_id=job.job_id,
            parent_ref=parent_ref,
            subtask_count=len(subtasks) if isinstance(subtasks, list) else 0,
        )
        return {
            "success": True,
            "parent_job_id": parent_ref,
            "subtasks_planned": subtasks if isinstance(subtasks, list) else [],
            "status": "delegated",
        }


class JobExecutor:
    """Dispatches jobs to earning strategies, n8n, consulting, or sub-task handlers."""

    def __init__(
        self,
        config: Config,
        strategy_manager: Optional["EarningStrategyManager"] = None,
        registry: Optional[ServiceRegistry] = None,
        n8n_composer: Optional[N8nWorkflowComposer] = None,
        consulting_handler: Optional[ConsultingJobHandler] = None,
        subtask_handler: Optional[SubTaskHandler] = None,
    ):
        self.config = config
        self.strategy_manager = strategy_manager
        self.registry = registry or default_service_registry()
        self.n8n_composer = n8n_composer or N8nWorkflowComposer(config)
        self.consulting_handler = consulting_handler or ConsultingJobHandler()
        self.subtask_handler = subtask_handler or SubTaskHandler()

    async def execute(self, job: Job) -> JobResult:
        now = datetime.utcnow()
        job.updated_at = now
        job.status = JobStatus(state="running", message="Executing", updated_at=now)

        try:
            logger.debug(
                "Executing job against manifest",
                category=job.category,
                manifest_entries=len(self.registry.by_category(job.category)),
            )
            if job.category == "data_intelligence":
                data = await self._run_data_intelligence(job)
            elif job.category == "workflow_automation":
                data = await self.n8n_composer.dispatch(job)
            elif job.category == "consulting":
                data = await self.consulting_handler.handle(job)
            else:
                data = await self.subtask_handler.handle(job)

            success = bool(data.get("success", False))
            end = datetime.utcnow()
            job.updated_at = end
            job.status = JobStatus(
                state="completed" if success else "failed",
                message=data.get("error") or data.get("summary"),
                updated_at=end,
            )
            return JobResult(
                job_id=job.job_id,
                success=success,
                category=job.category,
                completed_at=end,
                summary=_summarize(data, success),
                data=data,
                error_message=data.get("error") if not success else None,
            )
        except Exception as e:
            logger.exception("Job execution error", job_id=job.job_id)
            end = datetime.utcnow()
            job.updated_at = end
            job.status = JobStatus(state="failed", message=str(e), updated_at=end)
            return JobResult(
                job_id=job.job_id,
                success=False,
                category=job.category,
                completed_at=end,
                summary="Execution raised an exception",
                data={},
                error_message=str(e),
            )

    async def _run_data_intelligence(self, job: Job) -> Dict[str, Any]:
        if not self.strategy_manager:
            return {
                "success": False,
                "error": "EarningStrategyManager not configured",
            }
        strategy_name = job.metadata.get("strategy") or job.classification.get(
            "strategy", "fee_intelligence"
        )
        parameters: Dict[str, Any] = dict(job.metadata.get("strategy_parameters", {}))
        execution = await self.strategy_manager.execute_strategy(strategy_name, parameters)
        return {
            "success": execution.success,
            "strategy_name": execution.strategy_name,
            "earnings_sats": execution.earnings_sats,
            "price_charged_sats": execution.price_charged_sats,
            "error": execution.error_message,
            "execution_time_seconds": execution.execution_time_seconds,
        }


def _summarize(data: Dict[str, Any], success: bool) -> str:
    if not success:
        return str(data.get("error", "failed"))
    if "strategy_name" in data:
        return f"Strategy {data['strategy_name']} completed"
    if data.get("handoff"):
        return f"Consulting handoff: {data.get('handoff')}"
    if data.get("status") == "delegated":
        return "Sub-tasks delegated"
    if "status_code" in data:
        return f"n8n accepted job (HTTP {data['status_code']})"
    return "Completed"
