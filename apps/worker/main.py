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


@app.post("/jobs", status_code=202)
async def create_job(
    request: Request,
    background: BackgroundTasks,
    signature: str | None = Header(default=None, alias=HMAC_HEADER),
    timestamp: str | None = Header(default=None, alias=HMAC_TIMESTAMP_HEADER),
):
    secret = os.environ.get("WORKER_SHARED_SECRET")
    if not secret:
        raise HTTPException(500, "server not configured (missing secret)")

    if not signature or not timestamp:
        raise HTTPException(401, "missing signature headers")

    raw = await request.body()
    body_text = raw.decode("utf-8")

    if not verify_signature(secret, timestamp, body_text, signature):
        raise HTTPException(401, "invalid signature")

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
    except Exception as e:  # noqa: BLE001
        log.exception("Dispatch failed for job %s: %s", payload.jobId, e)
