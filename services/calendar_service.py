from __future__ import annotations
from typing import List, Dict, Any
from googleapiclient.discovery import build
from services.google_auth import build_credentials
from datetime import datetime, timedelta, timezone
import logging

logger = logging.getLogger(__name__)


def list_upcoming_events(user, days: int = 7, max_results: int = 10) -> List[Dict[str, Any]]:
    creds = build_credentials(user)
    if not creds:
        return [{"error": "Google not connected."}]
    try:
        service = build("calendar", "v3", credentials=creds, cache_discovery=False)
        now = datetime.now(timezone.utc)
        end = now + timedelta(days=days)
        events_result = service.events().list(
            calendarId="primary",
            timeMin=now.isoformat(),
            timeMax=end.isoformat(),
            maxResults=max_results,
            singleEvents=True,
            orderBy="startTime",
        ).execute()
        events = events_result.get("items", [])
        out = []
        for e in events:
            start = e["start"].get("dateTime", e["start"].get("date"))
            out.append({
                "summary": e.get("summary"),
                "start": start,
                "end": e["end"].get("dateTime", e["end"].get("date")),
                "location": e.get("location"),
                "description": (e.get("description") or "")[:300],
            })
        return out
    except Exception as e:
        logger.exception("Calendar list failed")
        return [{"error": str(e)}]


def create_event(user, summary: str, start_iso: str, end_iso: str, description: str = "") -> Dict[str, Any]:
    creds = build_credentials(user)
    if not creds:
        return {"error": "Google not connected."}
    try:
        service = build("calendar", "v3", credentials=creds, cache_discovery=False)
        event = {
            "summary": summary,
            "description": description,
            "start": {"dateTime": start_iso, "timeZone": "UTC"},
            "end": {"dateTime": end_iso, "timeZone": "UTC"},
        }
        created = service.events().insert(calendarId="primary", body=event).execute()
        return {"id": created.get("id"), "htmlLink": created.get("htmlLink"), "summary": summary}
    except Exception as e:
        return {"error": str(e)}
