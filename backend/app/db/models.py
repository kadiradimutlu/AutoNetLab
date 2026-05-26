from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String(120), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    role: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    student_id: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True, index=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    lab_sessions: Mapped[list["LabSessionRecord"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )


class LabSessionRecord(Base):
    __tablename__ = "lab_sessions"

    session_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    student_id: Mapped[str] = mapped_column(String(120), ForeignKey("users.username"), index=True, nullable=False)
    difficulty: Mapped[str] = mapped_column(String(40), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(40), index=True, nullable=False)
    topology_template: Mapped[str] = mapped_column(String(120), nullable=False)
    lab_name: Mapped[str] = mapped_column(String(160), nullable=False)
    topology_file: Mapped[str] = mapped_column(Text, nullable=False)
    topology_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    cli_access_json: Mapped[list] = mapped_column(JSON, nullable=False)
    injected_errors_json: Mapped[list] = mapped_column(JSON, nullable=False)
    topic_performance_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    passed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)

    user: Mapped[User] = relationship(back_populates="lab_sessions")
    validation_result: Mapped["ValidationResultRecord | None"] = relationship(
        back_populates="lab_session",
        cascade="all, delete-orphan",
        uselist=False,
    )
    validation_attempts: Mapped[list["ValidationAttemptRecord"]] = relationship(
        back_populates="lab_session",
        cascade="all, delete-orphan",
        order_by="ValidationAttemptRecord.attempt_number",
    )
    recommendations: Mapped[list["RecommendationRecord"]] = relationship(
        back_populates="lab_session",
        cascade="all, delete-orphan",
    )


class ValidationResultRecord(Base):
    __tablename__ = "validation_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(
        String(80),
        ForeignKey("lab_sessions.session_id"),
        unique=True,
        index=True,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    checks_json: Mapped[list] = mapped_column(JSON, nullable=False)
    recommendations_json: Mapped[list] = mapped_column(JSON, nullable=False)
    raw_result_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    lab_session: Mapped[LabSessionRecord] = relationship(back_populates="validation_result")


class ValidationAttemptRecord(Base):
    __tablename__ = "validation_attempts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(
        String(80),
        ForeignKey("lab_sessions.session_id"),
        index=True,
        nullable=False,
    )
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    passed_checks: Mapped[int] = mapped_column(Integer, nullable=False)
    failed_checks: Mapped[int] = mapped_column(Integer, nullable=False)
    checks_json: Mapped[list] = mapped_column(JSON, nullable=False)
    recommendations_json: Mapped[list] = mapped_column(JSON, nullable=False)
    raw_result_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)

    lab_session: Mapped[LabSessionRecord] = relationship(back_populates="validation_attempts")


class RecommendationRecord(Base):
    __tablename__ = "recommendations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(
        String(80),
        ForeignKey("lab_sessions.session_id"),
        index=True,
        nullable=False,
    )
    source: Mapped[str] = mapped_column(String(80), nullable=False)
    fallback_used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    recommendations_json: Mapped[list] = mapped_column(JSON, nullable=False)
    raw_payload_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    lab_session: Mapped[LabSessionRecord] = relationship(back_populates="recommendations")
