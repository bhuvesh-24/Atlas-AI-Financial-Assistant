from __future__ import annotations
from typing import List, Dict, Any
from googleapiclient.discovery import build
from services.google_auth import build_credentials
import logging

logger = logging.getLogger(__name__)


def search_files(user, query: str, max_results: int = 8) -> List[Dict[str, Any]]:
    creds = build_credentials(user)
    if not creds:
        return [{"error": "Google not connected."}]
    try:
        service = build("drive", "v3", credentials=creds, cache_discovery=False)
        q = f"fullText contains '{query}' and trashed = false"
        results = service.files().list(
            q=q,
            pageSize=max_results,
            fields="files(id, name, mimeType, modifiedTime, webViewLink)",
        ).execute()
        return results.get("files", [])
    except Exception as e:
        logger.exception("Drive search failed")
        return [{"error": str(e)}]


def get_sheet_preview(user, spreadsheet_id: str, range_name: str = "A1:Z50") -> Dict[str, Any]:
    creds = build_credentials(user)
    if not creds:
        return {"error": "Google not connected."}
    try:
        service = build("sheets", "v4", credentials=creds, cache_discovery=False)
        result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id, range=range_name
        ).execute()
        values = result.get("values", [])
        return {
            "spreadsheet_id": spreadsheet_id,
            "range": range_name,
            "rows": len(values),
            "preview": values[:30],
        }
    except Exception as e:
        return {"error": str(e)}
