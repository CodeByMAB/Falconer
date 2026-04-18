"""Route job requests from any channel through vLLM classification to executors."""

import json
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from openai import AsyncOpenAI

from ..config import Config
from ..logging import get_logger
from .executor import JobExecutor
from .persistence import JobHistoryStore
from .schema import Job, JobCategory, JobPriority, JobRequest, JobResult, JobStatus

logger = get_logger(__name__)

_VALID_CATEGORIES = frozenset(
    {"data_intelligence", "workflow_automation", "consulting", "agent_collaboration"}
)
_VALID_PRIORITIES = frozenset({"low", "standard", "high", "critical"})


class JobRouter:
    """Accepts `JobRequest` from any channel, classifies via vLLM, runs `JobExecutor`."""

    def __init__(
        self,
        config: Config,
        executor: JobExecutor,
        store: Optional[JobHistoryStore] = None,
    ):
        self.config = config
        self.executor = executor
        self.store = store or JobHistoryStore()
        self.vllm_model = config.vllm_model
        self.vllm_base_url = config.vllm_base_url

    async def route(self, request: JobRequest) -> Tuple[Job, JobResult]:
        """Classify (if needed), persist, execute, persist outcome."""
        job = await self._request_to_job(request)
        self.store.save_job(job)
        result = await self.executor.execute(job)
        self.store.save_job(job)
        self.store.append_result(result)
        return job, result

    async def _request_to_job(self, request: JobRequest) -> Job:
        classification: Dict[str, Any] = {}
        category: JobCategory
        priority: JobPriority

        if request.category is not None and request.priority is not None:
            category = request.category
            priority = request.priority
        elif request.category is not None:
            category = request.category
            priority = request.priority or "standard"
        else:
            classification = await self._classify_with_vllm(request)
            category = classification.get("category", "data_intelligence")
            if category not in _VALID_CATEGORIES:
                category = "data_intelligence"
            priority = classification.get("priority", "standard")
            if priority not in _VALID_PRIORITIES:
                priority = "standard"
            if request.priority is not None:
                priority = request.priority

        if priority not in _VALID_PRIORITIES:
            priority = "standard"

        now = datetime.utcnow()
        return Job(
            created_at=now,
            updated_at=now,
            status=JobStatus(state="queued", message="Routed", updated_at=now),
            category=category,
            priority=priority,
            channel=request.channel,
            text=request.text,
            metadata=dict(request.metadata),
            client_ref=request.client_ref,
            classification=classification,
        )

    async def _classify_with_vllm(self, request: JobRequest) -> Dict[str, Any]:
        prompt = _classification_prompt(request)
        try:
            raw = await self._query_vllm(prompt)
            parsed = _parse_classification_json(raw)
            if parsed:
                return parsed
        except Exception as e:
            logger.warning("vLLM classification failed, using defaults", error=str(e))
        return {
            "category": "data_intelligence",
            "priority": "standard",
            "strategy": "fee_intelligence",
            "reasoning": "fallback",
        }

    async def _query_vllm(self, prompt: str) -> str:
        api_key = self.config.vllm_api_key or "dummy"
        client = AsyncOpenAI(
            base_url=self.vllm_base_url,
            api_key=api_key,
        )
        response = await client.chat.completions.create(
            model=self.vllm_model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are Falconer's job router. Always respond with a single "
                        "JSON object, no markdown."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
        )
        content = response.choices[0].message.content
        return content or ""


def _classification_prompt(request: JobRequest) -> str:
    return f"""
Classify this work request for Falconer.

Request text:
{request.text}

Channel: {request.channel}
Extra metadata (JSON): {json.dumps(request.metadata, default=str)}

Respond with JSON only:
{{
  "category": "data_intelligence" | "workflow_automation" | "consulting" | "agent_collaboration",
  "priority": "low" | "standard" | "high" | "critical",
  "strategy": "optional earning strategy name for data_intelligence (e.g. fee_intelligence)",
  "reasoning": "short explanation"
}}
"""


def _parse_classification_json(response: str) -> Optional[Dict[str, Any]]:
    try:
        try:
            data = json.loads(response)
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass
        start = response.find("{")
        if start == -1:
            return None
        depth = 0
        end = start
        for i in range(start, len(response)):
            if response[i] == "{":
                depth += 1
            elif response[i] == "}":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        if depth != 0:
            return None
        data = json.loads(response[start:end])
        if isinstance(data, dict):
            return data
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning("Could not parse classification JSON", error=str(e))
    return None
