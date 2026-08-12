"""Extract text from uploaded PDFs, DOCX, XLSX, CSV, images."""
from __future__ import annotations
import os
import logging
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

UPLOAD_DIR = Path("/app/data/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def extract_text(file_path: str, file_type: str) -> Dict[str, Any]:
    file_type = file_type.lower().lstrip(".")
    try:
        if file_type == "pdf":
            return _extract_pdf(file_path)
        elif file_type in ("docx", "doc"):
            return _extract_docx(file_path)
        elif file_type in ("xlsx", "xls"):
            return _extract_xlsx(file_path)
        elif file_type == "csv":
            return _extract_csv(file_path)
        elif file_type in ("png", "jpg", "jpeg", "webp", "gif"):
            return {"type": "image", "path": file_path, "note": "Image ready for vision model"}
        else:
            return {"error": f"Unsupported file type: {file_type}"}
    except Exception as e:
        logger.exception("Extraction failed for %s", file_path)
        return {"error": str(e)}


def _extract_pdf(path: str) -> Dict[str, Any]:
    import pdfplumber
    text_parts = []
    with pdfplumber.open(path) as pdf:
        for i, page in enumerate(pdf.pages[:40]):  # limit pages
            t = page.extract_text() or ""
            if t.strip():
                text_parts.append(f"--- Page {i+1} ---\n{t}")
    full = "\n\n".join(text_parts)
    return {
        "type": "pdf",
        "pages_extracted": min(len(pdf.pages), 40),
        "text": full[:60000],  # hard cap for context
        "char_count": len(full),
    }


def _extract_docx(path: str) -> Dict[str, Any]:
    from docx import Document
    doc = Document(path)
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    full = "\n".join(paragraphs)
    return {
        "type": "docx",
        "paragraphs": len(paragraphs),
        "text": full[:60000],
        "char_count": len(full),
    }


def _extract_xlsx(path: str) -> Dict[str, Any]:
    import pandas as pd
    xl = pd.ExcelFile(path)
    sheets_summary = []
    full_text_parts = []
    for sheet in xl.sheet_names[:8]:
        df = pd.read_excel(xl, sheet_name=sheet, nrows=200)
        sheets_summary.append({
            "name": sheet,
            "rows": len(df),
            "columns": list(df.columns.astype(str)),
            "preview": df.head(15).to_string(index=False),
        })
        full_text_parts.append(f"=== Sheet: {sheet} ===\n{df.head(50).to_string()}")
    return {
        "type": "xlsx",
        "sheets": sheets_summary,
        "text": "\n\n".join(full_text_parts)[:60000],
    }


def _extract_csv(path: str) -> Dict[str, Any]:
    import pandas as pd
    df = pd.read_csv(path, nrows=500)
    return {
        "type": "csv",
        "rows": len(df),
        "columns": list(df.columns.astype(str)),
        "preview": df.head(20).to_string(index=False),
        "text": df.head(100).to_string()[:40000],
        "describe": df.describe(include="all").to_string()[:8000] if not df.empty else "",
    }


def save_upload(file_bytes: bytes, filename: str, user_id: int) -> str:
    from time import time
    safe_name = "".join(c for c in filename if c.isalnum() or c in "._-")[:120]
    user_dir = UPLOAD_DIR / str(user_id)
    user_dir.mkdir(parents=True, exist_ok=True)
    path = user_dir / f"{int(time())}_{safe_name}"
    path.write_bytes(file_bytes)
    return str(path)
