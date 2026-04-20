"""Export utilities — MD to DOCX and PDF conversion."""

import subprocess
import sys
from pathlib import Path

from config import EXPORT_SCRIPT


def export_docx(md_path: Path) -> Path | None:
    """Convert MD to DOCX using existing export-docx.mjs script."""
    docx_path = md_path.with_suffix(".docx")
    if not EXPORT_SCRIPT.exists():
        print(f"[WARN] export-docx.mjs not found at {EXPORT_SCRIPT}", file=sys.stderr)
        return None

    try:
        result = subprocess.run(
            ["node", str(EXPORT_SCRIPT), str(md_path)],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(md_path.parent),
        )
        if result.returncode == 0 and docx_path.exists():
            print(f"[EXPORT] DOCX: {docx_path}", file=sys.stderr)
            return docx_path
        else:
            print(f"[WARN] DOCX export failed: {result.stderr[:200]}", file=sys.stderr)
            return None
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        print(f"[WARN] DOCX export error: {e}", file=sys.stderr)
        return None


def export_pdf(md_path: Path) -> Path | None:
    """Convert MD to PDF using pandoc (optional)."""
    pdf_path = md_path.with_suffix(".pdf")
    try:
        result = subprocess.run(
            ["pandoc", str(md_path), "-o", str(pdf_path),
             "--pdf-engine=weasyprint", "-V", "lang=de"],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode == 0 and pdf_path.exists():
            print(f"[EXPORT] PDF: {pdf_path}", file=sys.stderr)
            return pdf_path
        else:
            print(f"[WARN] PDF export failed (pandoc): {result.stderr[:200]}", file=sys.stderr)
            return None
    except FileNotFoundError:
        print("[INFO] pandoc not installed — skipping PDF export", file=sys.stderr)
        return None
    except subprocess.TimeoutExpired:
        print("[WARN] PDF export timed out", file=sys.stderr)
        return None
