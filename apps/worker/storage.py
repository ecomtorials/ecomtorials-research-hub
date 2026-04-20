"""Supabase Storage helpers — uploads MD/DOCX artifacts to the private bucket."""
from __future__ import annotations

import logging
import os
from pathlib import Path

from supabase_client import get_supabase

log = logging.getLogger(__name__)


def get_bucket() -> str:
    return os.environ.get("ARTIFACT_BUCKET", "research-reports")


def upload_file(job_id: str, file_path: Path, kind: str) -> tuple[str, int]:
    """Upload to {bucket}/{job_id}/{kind}/{filename}. Returns (storage_path, size)."""
    data = file_path.read_bytes()
    storage_path = f"{job_id}/{kind}/{file_path.name}"
    sb = get_supabase()
    bucket = get_bucket()
    content_type = _content_type_for(file_path)
    try:
        sb.storage.from_(bucket).upload(
            path=storage_path,
            file=data,
            file_options={"content-type": content_type, "upsert": "true"},
        )
    except Exception as e:  # noqa: BLE001
        log.exception("Storage upload failed for %s: %s", storage_path, e)
        raise
    log.info("Uploaded %s to storage (%d bytes)", storage_path, len(data))
    return storage_path, len(data)


def _content_type_for(path: Path) -> str:
    suf = path.suffix.lower()
    return {
        ".md": "text/markdown; charset=utf-8",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".pdf": "application/pdf",
        ".json": "application/json; charset=utf-8",
        ".txt": "text/plain; charset=utf-8",
    }.get(suf, "application/octet-stream")
