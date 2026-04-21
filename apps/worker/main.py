"""FastAPI entry point for the research-worker.

Responsibilities:
- Accept signed POST /jobs requests from the Next.js frontend
- Verify HMAC signature
- Dispatch to the appropriate mode runner as a background task
- Also expose /healthz for Railway

The worker does NOT authenticate users directly — it trusts the HMAC signature.
Only the Next.js API route may call this endpoint.
"""
from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, Header, HTTPException, Request
from pydantic import BaseModel, Field

load_dotenv()

from hmac_verify import HMAC_HEADER, HMAC_TIMESTAMP_HEADER, verify_signature  # noqa: E402
from modes import run_angle, run_custom, run_full, run_ump_only  # noqa: E402
from progress import (  # noqa: E402
    JobCanceled,
    clear_canceled,
    mark_canceled,
    mark_job_finished,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("research-worker")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    secret = os.environ.get("WORKER_SHARED_SECRET")
    if not secret:
        log.error("WORKER_SHARED_SECRET is not set — requests will be rejected.")
    else:
        log.info("Worker ready. HMAC secret loaded (%d chars).", len(secret))
    yield


app = FastAPI(title="ecomtorials research-worker", lifespan=lifespan)


class JobPayload(BaseModel):
    jobId: str
    clientId: str
    mode: str = Field(pattern=r"^(full|angle|ump_only|custom)$")
    customSteps: list[str] | None = None
    sourceJobId: str | None = None
    url: str
    brand: str
    productName: str | None = None
    angle: str


@app.get("/healthz")
async def healthz():
    return {"ok": True, "service": "research-worker"}


async def _verify_hmac(request: Request, signature: str | None, timestamp: str | None) -> str:
    """Shared HMAC verification — returns the raw body text for downstream parsing."""
    secret = os.environ.get("WORKER_SHARED_SECRET")
    if not secret:
        raise HTTPException(500, "server not configured (missing secret)")
    if not signature or not timestamp:
        raise HTTPException(401, "missing signature headers")
    raw = await request.body()
    body_text = raw.decode("utf-8")
    if not verify_signature(secret, timestamp, body_text, signature):
        raise HTTPException(401, "invalid signature")
    return body_text


@app.post("/jobs/{job_id}/cancel", status_code=202)
async def cancel_job(
    job_id: str,
    request: Request,
    signature: str | None = Header(default=None, alias=HMAC_HEADER),
    timestamp: str | None = Header(default=None, alias=HMAC_TIMESTAMP_HEADER),
):
    """Flag a running job for cancellation.

    The in-memory flag is checked cooperatively at every pipeline step boundary
    (see progress.start_step). Work already in-flight (an LLM call or tool call)
    finishes normally before we bail out at the next checkpoint. The web API
    also writes status=cancelled to the DB so the UI updates immediately even
    if the worker is momentarily unreachable.
    """
    await _verify_hmac(request, signature, timestamp)
    mark_canceled(job_id)
    log.info("Cancel requested for job %s", job_id)
    return {"canceled": True, "jobId": job_id}


@app.post("/jobs", status_code=202)
async def create_job(
    request: Request,
    background: BackgroundTasks,
    signature: str | None = Header(default=None, alias=HMAC_HEADER),
    timestamp: str | None = Header(default=None, alias=HMAC_TIMESTAMP_HEADER),
):
    body_text = await _verify_hmac(request, signature, timestamp)

    try:
        payload = JobPayload.model_validate_json(body_text)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(400, f"invalid payload: {e}")

    log.info("Accepted job %s (mode=%s, brand=%s)", payload.jobId, payload.mode, payload.brand)

    # Schedule as background task. BackgroundTasks runs after response is sent.
    background.add_task(_dispatch, payload)
    return {"accepted": True, "jobId": payload.jobId}


async def _dispatch(payload: JobPayload) -> None:
    try:
        if payload.mode == "full":
            await run_full(
                job_id=payload.jobId,
                client_id=payload.clientId,
                url=payload.url,
                brand=payload.brand,
                angle=payload.angle,
                product_name=payload.productName,
            )
        elif payload.mode == "angle":
            await run_angle(
                job_id=payload.jobId,
                client_id=payload.clientId,
                url=payload.url,
                brand=payload.brand,
                angle=payload.angle,
                product_name=payload.productName,
            )
        elif payload.mode == "ump_only":
            if not payload.sourceJobId:
                log.error("ump_only job %s missing sourceJobId", payload.jobId)
                return
            await run_ump_only(
                job_id=payload.jobId,
                client_id=payload.clientId,
                url=payload.url,
                brand=payload.brand,
                angle=payload.angle,
                product_name=payload.productName,
                source_job_id=payload.sourceJobId,
            )
        elif payload.mode == "custom":
            await run_custom(
                job_id=payload.jobId,
                client_id=payload.clientId,
                url=payload.url,
                brand=payload.brand,
                angle=payload.angle,
                product_name=payload.productName,
                steps=payload.customSteps or [],
            )
        else:
            log.error("Unknown mode: %s", payload.mode)
    except JobCanceled:
        log.info("Job %s cancelled cooperatively at step boundary", payload.jobId)
        # Web API already wrote status=cancelled before calling us; still finalize
        # finished_at so duration calculations work, and clear the in-memory flag.
        try:
            mark_job_finished(
                payload.jobId,
                status="cancelled",
                cost_usd=0.0,
                quality_score=None,
                error="cancelled by user",
            )
        except Exception as mark_err:  # noqa: BLE001
            log.error("Failed to finalize cancelled job %s: %s", payload.jobId, mark_err)
        clear_canceled(payload.jobId)
    except Exception as e:  # noqa: BLE001
        log.exception("Dispatch failed for job %s: %s", payload.jobId, e)
        # Mark the row failed so the frontend stops spinning forever.
        try:
            mark_job_finished(
                payload.jobId,
                status="failed",
                cost_usd=0.0,
                quality_score=None,
                error=str(e)[:500],
            )
        except Exception as mark_err:  # noqa: BLE001
            log.error("Also failed to mark job %s as failed: %s", payload.jobId, mark_err)
        clear_canceled(payload.jobId)
