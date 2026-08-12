"""Lightweight FastAPI server for Google OAuth callback."""
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
import uvicorn
import logging
from services.google_auth import exchange_code
from db.session import AsyncSessionLocal
from db.models import User
from sqlalchemy import select
from datetime import datetime, timezone

logger = logging.getLogger(__name__)
app = FastAPI(title="Atlas OAuth")


@app.get("/oauth/callback")
async def oauth_callback(request: Request):
    params = dict(request.query_params)
    code = params.get("code")
    state = params.get("state")
    error = params.get("error")

    if error:
        return HTMLResponse(
            f"<h2>Google authorization failed</h2><p>{error}</p><p>You can close this tab and return to Telegram.</p>",
            status_code=400,
        )
    if not code or not state:
        return HTMLResponse("<h2>Missing code or state</h2>", status_code=400)

    result = exchange_code(code, state)
    if "error" in result:
        return HTMLResponse(f"<h2>Error</h2><p>{result['error']}</p>", status_code=400)

    telegram_user_id = result["telegram_user_id"]
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(User).where(User.telegram_id == str(telegram_user_id)))
        user = res.scalar_one_or_none()
        if user:
            user.google_access_token = result["access_token"]
            user.google_refresh_token = result.get("refresh_token") or user.google_refresh_token
            if result.get("expiry"):
                try:
                    user.google_token_expiry = datetime.fromisoformat(result["expiry"])
                except Exception:
                    pass
            user.google_scopes = result.get("scopes", [])
            user.google_connected = True
            await session.commit()

    return HTMLResponse(
        """
        <html><body style="font-family:system-ui;text-align:center;padding:60px">
        <h1>✅ Connected</h1>
        <p>Your Google account is now linked to Atlas.</p>
        <p>Return to Telegram — I can now search Gmail, Calendar and Drive for you.</p>
        </body></html>
        """
    )


@app.get("/health")
async def health():
    return {"status": "ok"}


def run_oauth_server(port: int = 8000):
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="warning")
