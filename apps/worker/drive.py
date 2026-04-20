"""Google Drive uploader — service-account based.

Uploads artifacts (MD/DOCX) to a subfolder under `clients.drive_folder_id`.
If the client has no drive folder, uploads are skipped (returns None).
"""
from __future__ import annotations

import base64
import json
import logging
import os
from datetime import date
from pathlib import Path
from typing import Any

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

log = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/drive"]
SUBFOLDER_MIME = "application/vnd.google-apps.folder"


def _load_credentials() -> service_account.Credentials | None:
    raw = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
    if not raw:
        return None
    # Accept either raw JSON or base64-encoded JSON
    try:
        info = json.loads(raw)
    except json.JSONDecodeError:
        try:
            info = json.loads(base64.b64decode(raw).decode("utf-8"))
        except Exception as e:  # noqa: BLE001
            log.warning("Failed to parse GOOGLE_SERVICE_ACCOUNT_JSON: %s", e)
            return None
    return service_account.Credentials.from_service_account_info(info, scopes=SCOPES)


def _drive_service() -> Any:
    creds = _load_credentials()
    if creds is None:
        raise RuntimeError("GOOGLE_SERVICE_ACCOUNT_JSON not configured")
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def _find_or_create_subfolder(service: Any, parent_id: str, name: str) -> str:
    """Find existing subfolder or create new one. Returns folder id."""
    q = (
        f"mimeType='{SUBFOLDER_MIME}' and "
        f"name='{name}' and "
        f"'{parent_id}' in parents and "
        f"trashed=false"
    )
    resp = service.files().list(q=q, fields="files(id, name)", pageSize=1, supportsAllDrives=True, includeItemsFromAllDrives=True).execute()
    files = resp.get("files", [])
    if files:
        return files[0]["id"]
    folder = service.files().create(
        body={"name": name, "mimeType": SUBFOLDER_MIME, "parents": [parent_id]},
        fields="id",
        supportsAllDrives=True,
    ).execute()
    return folder["id"]


def upload_artifacts(
    parent_folder_id: str,
    mode: str,
    brand: str,
    files: list[Path],
) -> tuple[str, list[tuple[Path, str, str]]]:
    """Upload each file to a dated subfolder. Returns (folder_url, [(path, file_id, web_url), ...])."""
    service = _drive_service()
    today = date.today().isoformat()
    subfolder_name = f"Research {today} - {mode} - {brand}"[:120]
    sub_id = _find_or_create_subfolder(service, parent_folder_id, subfolder_name)
    folder_url = f"https://drive.google.com/drive/folders/{sub_id}"

    results: list[tuple[Path, str, str]] = []
    for f in files:
        if not f.exists():
            continue
        mime = _guess_mime(f)
        media = MediaFileUpload(str(f), mimetype=mime, resumable=False)
        uploaded = service.files().create(
            body={"name": f.name, "parents": [sub_id]},
            media_body=media,
            fields="id, webViewLink",
            supportsAllDrives=True,
        ).execute()
        results.append((f, uploaded["id"], uploaded.get("webViewLink", "")))
        log.info("Uploaded %s to Drive (id=%s)", f.name, uploaded["id"])

    return folder_url, results


def _guess_mime(path: Path) -> str:
    suf = path.suffix.lower()
    return {
        ".md": "text/markdown",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".pdf": "application/pdf",
        ".json": "application/json",
    }.get(suf, "application/octet-stream")
