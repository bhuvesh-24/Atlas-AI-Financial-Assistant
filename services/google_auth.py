"""Google OAuth 2.0 for Gmail, Calendar, Drive, Sheets."""
from __future__ import annotations
import secrets
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List
from urllib.parse import urlencode

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request

from config import settings

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
]

# In-memory state store (replace with Redis in production)
_pending_states: Dict[str, Dict[str, Any]] = {}


def is_google_configured() -> bool:
    return bool(settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET)


def create_auth_url(telegram_user_id: str) -> Dict[str, str]:
    if not is_google_configured():
        return {"error": "Google OAuth is not configured on this deployment."}

    state = secrets.token_urlsafe(24)
    _pending_states[state] = {
        "telegram_user_id": telegram_user_id,
        "created_at": datetime.now(timezone.utc),
    }

    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [settings.GOOGLE_REDIRECT_URI],
            }
        },
        scopes=SCOPES,
        state=state,
    )
    flow.redirect_uri = settings.GOOGLE_REDIRECT_URI
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    return {"auth_url": auth_url, "state": state}


def exchange_code(code: str, state: str) -> Dict[str, Any]:
    if state not in _pending_states:
        return {"error": "Invalid or expired state. Please request a new connect link."}

    meta = _pending_states.pop(state)
    telegram_user_id = meta["telegram_user_id"]

    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [settings.GOOGLE_REDIRECT_URI],
            }
        },
        scopes=SCOPES,
        state=state,
    )
    flow.redirect_uri = settings.GOOGLE_REDIRECT_URI
    flow.fetch_token(code=code)
    creds = flow.credentials

    return {
        "telegram_user_id": telegram_user_id,
        "access_token": creds.token,
        "refresh_token": creds.refresh_token,
        "expiry": creds.expiry.isoformat() if creds.expiry else None,
        "scopes": list(creds.scopes or []),
    }


def build_credentials(user) -> Optional[Credentials]:
    if not user.google_access_token:
        return None
    creds = Credentials(
        token=user.google_access_token,
        refresh_token=user.google_refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        scopes=user.google_scopes or SCOPES,
    )
    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            # Caller should persist new token
        except Exception as e:
            logger.warning("Token refresh failed: %s", e)
            return None
    return creds


def cleanup_expired_states(max_age_minutes: int = 30):
    now = datetime.now(timezone.utc)
    expired = [
        s for s, m in _pending_states.items()
        if (now - m["created_at"]).total_seconds() > max_age_minutes * 60
    ]
    for s in expired:
        _pending_states.pop(s, None)
