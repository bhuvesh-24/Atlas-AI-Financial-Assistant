from __future__ import annotations
from typing import List, Dict, Any, Optional
from googleapiclient.discovery import build
from services.google_auth import build_credentials
import base64
import logging

logger = logging.getLogger(__name__)


def search_emails(user, query: str, max_results: int = 8) -> List[Dict[str, Any]]:
    creds = build_credentials(user)
    if not creds:
        return [{"error": "Google not connected or token expired. Ask the user to reconnect."}]
    try:
        service = build("gmail", "v1", credentials=creds, cache_discovery=False)
        results = service.users().messages().list(
            userId="me", q=query, maxResults=max_results
        ).execute()
        messages = results.get("messages", [])
        out = []
        for m in messages:
            msg = service.users().messages().get(
                userId="me", id=m["id"], format="metadata",
                metadataHeaders=["From", "Subject", "Date"]
            ).execute()
            headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
            out.append({
                "id": m["id"],
                "snippet": msg.get("snippet"),
                "from": headers.get("From"),
                "subject": headers.get("Subject"),
                "date": headers.get("Date"),
            })
        return out
    except Exception as e:
        logger.exception("Gmail search failed")
        return [{"error": str(e)}]
