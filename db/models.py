from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, Float, ForeignKey, JSON
)
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime, timezone

Base = declarative_base()


def utcnow():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    telegram_id = Column(String(64), unique=True, nullable=False, index=True)
    username = Column(String(128), nullable=True)
    first_name = Column(String(128), nullable=True)
    last_name = Column(String(128), nullable=True)

    # Onboarding & profile
    role = Column(String(64), nullable=True)  # Investor, Analyst, Founder, etc.
    verticals = Column(JSON, default=list)  # ["finance", "technology", ...]
    watchlist = Column(JSON, default=list)  # ["AAPL", "NVDA", ...]
    interests = Column(JSON, default=list)  # topics, sectors
    preferred_briefing_time = Column(String(16), nullable=True)  # "08:30"
    timezone = Column(String(64), default="Asia/Kolkata")
    onboarding_complete = Column(Boolean, default=False)
    onboarding_step = Column(String(64), default="welcome")

    # Preferences learned over time
    preferences = Column(JSON, default=dict)
    memory_notes = Column(Text, default="")  # free-form notes the AI keeps

    # Google OAuth tokens (encrypted in production)
    google_access_token = Column(Text, nullable=True)
    google_refresh_token = Column(Text, nullable=True)
    google_token_expiry = Column(DateTime, nullable=True)
    google_scopes = Column(JSON, default=list)
    google_connected = Column(Boolean, default=False)

    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)
    last_active = Column(DateTime, default=utcnow)

    # Relationships
    messages = relationship("Message", back_populates="user", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="user", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="user", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    role = Column(String(16), nullable=False)  # user / assistant / system
    content = Column(Text, nullable=False)
    message_type = Column(String(32), default="text")  # text, voice, image, document
    extra_data = Column(JSON, default=dict)  # file paths, tool results, etc.
    created_at = Column(DateTime, default=utcnow)

    user = relationship("User", back_populates="messages")


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    ticker = Column(String(32), nullable=False)
    condition = Column(String(32), nullable=False)  # percent_move, price_above, price_below
    threshold = Column(Float, nullable=False)
    direction = Column(String(8), default="any")  # up, down, any
    is_active = Column(Boolean, default=True)
    last_triggered = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utcnow)
    note = Column(Text, nullable=True)

    user = relationship("User", back_populates="alerts")


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    file_name = Column(String(256), nullable=False)
    file_type = Column(String(32), nullable=False)  # pdf, xlsx, csv, docx, image
    local_path = Column(String(512), nullable=True)
    extracted_text = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)
    extra_data = Column(JSON, default=dict)
    created_at = Column(DateTime, default=utcnow)

    user = relationship("User", back_populates="documents")


class ConversationState(Base):
    """Lightweight state for multi-turn flows (e.g. pending Google connect)."""
    __tablename__ = "conversation_states"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    state = Column(String(64), default="idle")
    context = Column(JSON, default=dict)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)
