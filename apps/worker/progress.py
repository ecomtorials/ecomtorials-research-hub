"""Job progress tracking — pushes step + job updates to Supabase.

Schema mirrors research.job_steps and research.jobs. All writes go via the
service-role client, bypassing RLS.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from supabase_client import get_supabase

log = logging.getLogger(__name__)

StepName = str  # see packages/shared/src/types.ts::PipelineStep
StepStatus = str  # 'pending'|'running'|'succeeded'|'failed'|'skipped'
JobStatus = str  # 'queued'|'running'|'succeeded'|...


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def update_job(job_id: str, **fields: Any) -> None:
    """Update fields on research.jobs. Any timestamptz values should be ISO strings."""
    sb = get_supabase()
    sb.schema("research").table("jobs").update(fields).eq("id", job_id).execute()


def mark_job_running(job_id: str) -> None:
    update_job(job_id, status="running", started_at=_now_iso())


def mark_job_finished(job_id: str, status: JobStatus, cost_usd: float, quality_score: float | None, error: str | None = None, drive_folder_url: str | None = None) -> None:
    update_job(
        job_id,
        status=status,
        finished_at=_now_iso(),
        cost_usd=round(cost_usd, 4),
        quality_score=quality_score,
        error=error,
        drive_folder_url=drive_folder_url,
    )


def start_step(job_id: str, step: StepName) -> None:
    sb = get_supabase()
    sb.schema("research").table("job_steps").upsert(
        {
            "job_id": job_id,
            "step": step,
            "status": "running",
            "started_at": _now_iso(),
        },
        on_conflict="job_id,step",
    ).execute()


def finish_step(
    job_id: str,
    step: StepName,
    status: StepStatus,
    cost_usd: float = 0.0,
    chars_produced: int | None = None,
    turns: int | None = None,
    log_text: str | None = None,
) -> None:
    sb = get_supabase()
    sb.schema("research").table("job_steps").upsert(
        {
            "job_id": job_id,
            "step": step,
            "status": status,
            "finished_at": _now_iso(),
            "cost_usd": round(cost_usd, 4),
            "chars_produced": chars_produced,
            "turns": turns,
            "log": log_text,
        },
        on_conflict="job_id,step",
    ).execute()


def register_artifact(
    job_id: str,
    kind: str,
    storage_path: str | None = None,
    drive_file_id: str | None = None,
    drive_url: str | None = None,
    size_bytes: int = 0,
) -> None:
    sb = get_supabase()
    sb.schema("research").table("job_artifacts").insert(
        {
            "job_id": job_id,
            "kind": kind,
            "storage_path": storage_path,
            "drive_file_id": drive_file_id,
            "drive_url": drive_url,
            "size_bytes": size_bytes,
        }
    ).execute()
