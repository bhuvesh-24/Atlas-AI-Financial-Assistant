from __future__ import annotations
from typing import List, Dict, Any
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from db.models import User, Message
from datetime import datetime, timezone


async def get_or_create_user(session: AsyncSession, telegram_id: str, username: str = None,
                             first_name: str = None, last_name: str = None) -> User:
    result = await session.execute(select(User).where(User.telegram_id == str(telegram_id)))
    user = result.scalar_one_or_none()
    if user:
        user.last_active = datetime.now(timezone.utc)
        if username:
            user.username = username
        await session.commit()
        return user
    user = User(
        telegram_id=str(telegram_id),
        username=username,
        first_name=first_name,
        last_name=last_name,
        verticals=["finance"],
        watchlist=[],
        interests=[],
        preferences={},
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def save_message(session: AsyncSession, user_id: int, role: str, content: str,
                       message_type: str = "text", extra: dict = None):
    msg = Message(
        user_id=user_id,
        role=role,
        content=content,
        message_type=message_type,
        extra_data=extra or {},
    )
    session.add(msg)
    await session.commit()


async def get_recent_messages(session: AsyncSession, user_id: int, limit: int = 16) -> List[Dict]:
    result = await session.execute(
        select(Message)
        .where(Message.user_id == user_id)
        .order_by(desc(Message.created_at))
        .limit(limit)
    )
    rows = result.scalars().all()
    # reverse to chronological
    return [{"role": m.role, "content": m.content} for m in reversed(rows)]


def build_user_context(user: User) -> str:
    parts = []
    name = user.first_name or user.username or "there"
    parts.append(f"Name: {name}")
    if user.role:
        parts.append(f"Role: {user.role}")
    if user.verticals:
        parts.append(f"Verticals: {', '.join(user.verticals)} (finance is primary)")
    if user.watchlist:
        parts.append(f"Watchlist: {', '.join(user.watchlist)}")
    if user.interests:
        parts.append(f"Interests: {', '.join(user.interests)}")
    if user.preferred_briefing_time:
        parts.append(f"Preferred briefing time: {user.preferred_briefing_time}")
    parts.append(f"Google connected: {'yes' if user.google_connected else 'no'}")
    if user.memory_notes:
        parts.append(f"Notes: {user.memory_notes[:800]}")
    if user.preferences:
        parts.append(f"Preferences: {user.preferences}")
    return "\n".join(parts)


async def extract_and_update_profile(session: AsyncSession, user: User, assistant_reply: str, user_message: str):
    """Lightweight heuristic + later can be LLM extraction. For MVP we keep simple updates via tools."""
    # Profile updates mainly happen through tools (update_watchlist) or explicit onboarding parsing.
    user.last_active = datetime.now(timezone.utc)
    await session.commit()
