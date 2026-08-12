from __future__ import annotations
import logging
from datetime import datetime, timezone
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select
from db.session import AsyncSessionLocal
from db.models import User, Alert
from services.market_data import get_quote
from ai.engine import generate_response
from ai.memory import save_message
from config import settings

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler(timezone=settings.TIMEZONE)


async def check_alerts(bot):
    """Background job: evaluate active price alerts."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Alert).where(Alert.is_active == True))
        alerts = result.scalars().all()
        for alert in alerts:
            try:
                q = get_quote(alert.ticker)
                price = q.get("price")
                change_pct = q.get("change_pct")
                if price is None:
                    continue
                triggered = False
                if alert.condition == "percent_move" and change_pct is not None:
                    if abs(change_pct) >= alert.threshold:
                        if alert.direction == "any" or \
                           (alert.direction == "up" and change_pct > 0) or \
                           (alert.direction == "down" and change_pct < 0):
                            triggered = True
                elif alert.condition == "price_above" and price >= alert.threshold:
                    triggered = True
                elif alert.condition == "price_below" and price <= alert.threshold:
                    triggered = True
                if triggered:
                    user = await session.get(User, alert.user_id)
                    if user:
                        msg = (
                            f"🔔 *Alert triggered*\n"
                            f"{alert.ticker} is at {price} ({change_pct:+.2f}% today).\n"
                            f"Condition: {alert.condition} {alert.threshold}"
                        )
                        await bot.send_message(chat_id=int(user.telegram_id), text=msg, parse_mode="Markdown")
                        alert.last_triggered = datetime.now(timezone.utc)
                        # one-shot for percent moves; keep absolute levels active
                        if alert.condition == "percent_move":
                            alert.is_active = False
                        await session.commit()
            except Exception:
                logger.exception("Alert check failed for %s", alert.ticker)


async def send_daily_briefings(bot):
    """Morning brief for users who opted in."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.onboarding_complete == True)
        )
        users = result.scalars().all()
        for user in users:
            if not user.watchlist and not user.interests:
                continue
            try:
                prompt = (
                    "Generate my personalized morning market brief based on my watchlist and interests. "
                    "Keep it under 250 words. Cover: overnight movers, important news, any upcoming earnings, "
                    "and one actionable observation. Skip if nothing material."
                )
                reply = await generate_response(session, user, prompt)
                if reply and "nothing material" not in reply.lower():
                    await bot.send_message(
                        chat_id=int(user.telegram_id),
                        text=f"☀️ *Morning Brief*\n\n{reply}",
                        parse_mode="Markdown",
                    )
                    await save_message(session, user.id, "assistant", reply)
            except Exception:
                logger.exception("Briefing failed for user %s", user.id)


def start_scheduler(bot):
    scheduler.add_job(check_alerts, "interval", minutes=5, args=[bot], id="alerts")
    scheduler.add_job(
        send_daily_briefings,
        "cron",
        hour=settings.DAILY_BRIEFING_HOUR,
        minute=settings.DAILY_BRIEFING_MINUTE,
        args=[bot],
        id="daily_brief",
    )
    scheduler.start()
    logger.info("Scheduler started")
