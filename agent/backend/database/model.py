from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSON
from datetime import datetime
from .session import Base

# Use SQLite JSON support (SQLAlchemy handles JSON for SQLite as Text with JSON serialization)
try:
    # Try to import JSON from PostgreSQL dialect, fallback to Text for SQLite
    from sqlalchemy.dialects.postgresql import JSON
except ImportError:
    JSON = Text  # Fallback for SQLite

class Session(Base):
    __tablename__ = "sessions"
    id = Column(String, primary_key=True, index=True)  # session_id
    title = Column(String, nullable=True)  # LLM-generated session title
    created_at = Column(DateTime, default=datetime.utcnow)

    messages = relationship("Message", back_populates="session")
    review_data = relationship("ReviewData", back_populates="session", uselist=False)

class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, ForeignKey("sessions.id"))
    role = Column(String)      # "user" or "assistant"
    content = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)

    session = relationship("Session", back_populates="messages")

class ReviewData(Base):
    __tablename__ = "review_data"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, ForeignKey("sessions.id"), index=True, nullable=True)  # Nullable for integrated reviews
    generation_type = Column(String, default="session")  # "session" or "integrated"

    # Structured review content - groups with knowledge cards and quiz questions
    review_groups = Column(JSON)  # JSON array of review groups
    aggregated_summary = Column(Text)  # Overall summary across all groups
    next_review_date = Column(DateTime)
    time_range_days = Column(Integer, nullable=True)  # Time range in days (7 or 30 for integrated reviews)

    # Status tracking
    generation_status = Column(String, default="pending")  # pending, generating, completed, failed
    generated_at = Column(DateTime)
    expires_at = Column(DateTime)  # Cache expiration time (default 24 hours)
    last_attempt_at = Column(DateTime)
    error_message = Column(Text)

    # Generation configuration (for retry with same parameters)
    generation_config = Column(JSON)  # Store generation parameters

    # User review status
    learned_cards = Column(JSON, default=[])  # IDs of learned knowledge cards
    completed_quizzes = Column(JSON, default=[])  # IDs of completed quiz questions
    last_reviewed_at = Column(DateTime)
    review_count = Column(Integer, default=0)

    # Relationships
    session = relationship("Session", back_populates="review_data")

class ReviewGenerationTask(Base):
    __tablename__ = "review_generation_tasks"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, ForeignKey("sessions.id"), index=True)
    task_type = Column(String)  # "initial", "update", "retry"
    status = Column(String)  # "pending", "running", "completed", "failed"
    priority = Column(Integer, default=0)  # Priority queue
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    error_message = Column(Text)

    # Associated ReviewData
    review_data_id = Column(Integer, ForeignKey("review_data.id"), nullable=True)

    # Relationships
    review_data = relationship("ReviewData", foreign_keys=[review_data_id])
    session = relationship("Session", foreign_keys=[session_id])