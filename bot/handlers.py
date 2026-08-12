from __future__ import annotations
import logging
import tempfile
import os
from pathlib import Path
from telegram import Update
from telegram.ext import ContextTypes
from sqlalchemy.ext.asyncio import AsyncSession
from db.session import AsyncSessionLocal
from ai.memory import get_or_create_user, save_message
from ai.engine import generate_response
from services.documents import extract_text, save_upload
from config import settings

logger = logging.getLogger(__name__)


async def start_or_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Single entry for all text messages — natural conversation, no commands."""
    if not update.message or not update.effective_user:
        return
    user_tg = update.effective_user
    text = (update.message.text or "").strip()
    if not text:
        return

    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(
            session,
            telegram_id=str(user_tg.id),
            username=user_tg.username,
            first_name=user_tg.first_name,
            last_name=user_tg.last_name,
        )
        await save_message(session, user.id, "user", text)

        # Lightweight onboarding kick-off
        if not user.onboarding_complete and user.onboarding_step == "welcome":
            user.onboarding_step = "role"
            await session.commit()

        reply = await generate_response(session, user, text)
        await save_message(session, user.id, "assistant", reply)

        # Mark onboarding complete after a few exchanges if role + watchlist exist
        if not user.onboarding_complete and user.role and (user.watchlist or user.interests):
            user.onboarding_complete = True
            user.onboarding_step = "done"
            await session.commit()

    # Telegram has 4096 char limit
    for chunk in _chunk(reply, 4000):
        await update.message.reply_text(chunk, parse_mode="Markdown")


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.document:
        return
    doc = update.message.document
    user_tg = update.effective_user
    file = await context.bot.get_file(doc.file_id)
    file_bytes = await file.download_as_bytearray()

    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(session, str(user_tg.id), user_tg.username, user_tg.first_name)
        path = save_upload(bytes(file_bytes), doc.file_name or "file", user.id)
        ext = (doc.file_name or "").split(".")[-1].lower()
        extracted = extract_text(path, ext)
        text_content = extracted.get("text") or extracted.get("error") or "Could not extract text."
        caption = update.message.caption or "Please summarize this document and highlight key insights."
        await save_message(session, user.id, "user", f"[Document: {doc.file_name}] {caption}", "document",
                           {"path": path, "type": ext})
        reply = await generate_response(session, user, caption, document_text=text_content)
        await save_message(session, user.id, "assistant", reply)

    for chunk in _chunk(reply, 4000):
        await update.message.reply_text(chunk, parse_mode="Markdown")


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.photo:
        return
    photo = update.message.photo[-1]
    user_tg = update.effective_user
    file = await context.bot.get_file(photo.file_id)
    file_bytes = await file.download_as_bytearray()

    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(session, str(user_tg.id), user_tg.username, user_tg.first_name)
        path = save_upload(bytes(file_bytes), "image.jpg", user.id)
        caption = update.message.caption or "Analyze this image / chart and tell me what matters."
        # For vision we pass a note; full vision requires multimodal model call (simplified here)
        await save_message(session, user.id, "user", f"[Image] {caption}", "image", {"path": path})
        # Simple text path; production would call Claude vision / GPT-4o vision
        reply = await generate_response(
            session, user,
            f"{caption}\n\n(An image was uploaded. Describe key visual takeaways if it is a chart or table; "
            "otherwise note that full vision analysis needs the multimodal endpoint enabled.)"
        )
        await save_message(session, user.id, "assistant", reply)

    for chunk in _chunk(reply, 4000):
        await update.message.reply_text(chunk, parse_mode="Markdown")


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.voice:
        return
    user_tg = update.effective_user
    voice = update.message.voice
    file = await context.bot.get_file(voice.file_id)
    file_bytes = await file.download_as_bytearray()

    transcript = await _transcribe(bytes(file_bytes))
    if not transcript:
        await update.message.reply_text("I couldn’t transcribe that voice note. Mind typing it?")
        return

    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(session, str(user_tg.id), user_tg.username, user_tg.first_name)
        await save_message(session, user.id, "user", transcript, "voice")
        reply = await generate_response(session, user, transcript)
        await save_message(session, user.id, "assistant", reply)

    for chunk in _chunk(reply, 4000):
        await update.message.reply_text(chunk, parse_mode="Markdown")


async def _transcribe(audio_bytes: bytes) -> str:
    if not settings.GROQ_API_KEY:
        return ""
    try:
        from groq import Groq
        client = Groq(api_key=settings.GROQ_API_KEY)
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name
        with open(tmp_path, "rb") as f:
            tr = client.audio.transcriptions.create(
                file=f,
                model="whisper-large-v3",
                response_format="text",
            )
        os.unlink(tmp_path)
        return tr if isinstance(tr, str) else getattr(tr, "text", "")
    except Exception as e:
        logger.exception("Transcription failed")
        return ""


def _chunk(text: str, size: int = 4000):
    while text:
        yield text[:size]
        text = text[size:]
