"""JSON-file persistence for job history (`data/jobs.json`)."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..logging import get_logger
from .schema import Job, JobResult, JobSummary

logger = get_logger(__name__)


class JobHistoryStore:
    """Store and query jobs and results using the same JSON pattern as PersistenceManager."""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.jobs_file = self.data_dir / "jobs.json"

    def save_job(self, job: Job) -> None:
        """Insert or replace a job record by job_id."""
        try:
            root = self._load_root()
            jobs = root.setdefault("jobs", {})
            if not isinstance(jobs, dict):
                jobs = {}
                root["jobs"] = jobs
            payload = job.model_dump(mode="json")
            jobs[job.job_id] = payload
            self._save_json(self.jobs_file, root)
            logger.info("Job saved", job_id=job.job_id, state=job.status.state)
        except Exception as e:
            logger.error("Failed to save job", job_id=job.job_id, error=str(e))
            raise

    def append_result(self, result: JobResult) -> None:
        """Append a result to the results list inside the jobs file."""
        try:
            root = self._load_root()
            results = root.get("results", [])
            if not isinstance(results, list):
                results = []
            results.append(result.model_dump(mode="json"))
            if len(results) > 2000:
                results = results[-2000:]
            root["results"] = results
            self._save_json(self.jobs_file, root)
            logger.info("Job result recorded", job_id=result.job_id, success=result.success)
        except Exception as e:
            logger.error("Failed to append job result", job_id=result.job_id, error=str(e))
            raise

    def load_job(self, job_id: str) -> Optional[Job]:
        jobs = self._load_jobs()
        data = jobs.get(job_id)
        if not data:
            return None
        return Job(**data)

    def list_jobs(
        self,
        limit: int = 100,
        category: Optional[str] = None,
    ) -> List[JobSummary]:
        jobs = self._load_jobs()
        summaries: List[JobSummary] = []
        for data in jobs.values():
            try:
                j = Job(**data)
            except Exception:
                continue
            if category is not None and j.category != category:
                continue
            summaries.append(
                JobSummary(
                    job_id=j.job_id,
                    created_at=j.created_at,
                    category=j.category,
                    priority=j.priority,
                    state=j.status.state,
                    channel=j.channel,
                )
            )
        summaries.sort(key=lambda s: s.created_at, reverse=True)
        return summaries[:limit]

    def load_results_for_job(self, job_id: str) -> List[JobResult]:
        root = self._load_root()
        raw = root.get("results", [])
        if not isinstance(raw, list):
            return []
        out: List[JobResult] = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            if item.get("job_id") != job_id:
                continue
            try:
                out.append(JobResult(**item))
            except Exception:
                continue
        return out

    def _load_jobs(self) -> Dict[str, Dict]:
        root = self._load_root()
        jobs = root.get("jobs", {})
        return jobs if isinstance(jobs, dict) else {}

    def _load_root(self) -> Dict[str, Any]:
        data = self._load_json(self.jobs_file, None)
        if data is None:
            return {"jobs": {}, "results": []}
        if isinstance(data, list):
            # Legacy: list-only file — migrate to dict keyed by id
            migrated: Dict[str, Dict] = {}
            for item in data:
                if isinstance(item, dict) and item.get("job_id"):
                    migrated[item["job_id"]] = item
            return {"jobs": migrated, "results": []}
        if isinstance(data, dict) and "jobs" in data:
            return data
        if isinstance(data, dict):
            return {"jobs": data, "results": []}
        return {"jobs": {}, "results": []}

    def _load_json(self, file_path: Path, default: Optional[Any]) -> Any:
        if not file_path.exists():
            return default
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(
                "Failed to load jobs JSON, using default",
                file=str(file_path),
                error=str(e),
            )
            return default

    def _save_json(self, file_path: Path, data: Dict[str, Any]) -> None:
        try:
            if file_path.exists():
                backup_path = file_path.with_suffix(".json.bak")
                file_path.rename(backup_path)

            def json_serializer(obj: Any) -> Any:
                if isinstance(obj, datetime):
                    return obj.isoformat()
                raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=json_serializer)

            backup_path = file_path.with_suffix(".json.bak")
            if backup_path.exists():
                backup_path.unlink()
        except Exception:
            backup_path = file_path.with_suffix(".json.bak")
            if backup_path.exists():
                backup_path.rename(file_path)
            raise
