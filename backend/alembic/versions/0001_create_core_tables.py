"""create core persistence tables

Revision ID: 0001_create_core_tables
Revises:
Create Date: 2026-05-15
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0001_create_core_tables"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("username", sa.String(length=120), nullable=False),
        sa.Column("display_name", sa.String(length=200), nullable=False),
        sa.Column("role", sa.String(length=40), nullable=False),
        sa.Column("student_id", sa.String(length=120), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("username"),
    )
    op.create_index("ix_users_role", "users", ["role"])
    op.create_index("ix_users_student_id", "users", ["student_id"])

    op.create_table(
        "lab_sessions",
        sa.Column("session_id", sa.String(length=80), nullable=False),
        sa.Column("student_id", sa.String(length=120), nullable=False),
        sa.Column("difficulty", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("topology_template", sa.String(length=120), nullable=False),
        sa.Column("lab_name", sa.String(length=160), nullable=False),
        sa.Column("topology_file", sa.Text(), nullable=False),
        sa.Column("topology_json", sa.JSON(), nullable=False),
        sa.Column("cli_access_json", sa.JSON(), nullable=False),
        sa.Column("injected_errors_json", sa.JSON(), nullable=False),
        sa.Column("topic_performance_json", sa.JSON(), nullable=True),
        sa.Column("score", sa.Integer(), nullable=True),
        sa.Column("passed", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["student_id"], ["users.username"]),
        sa.PrimaryKeyConstraint("session_id"),
    )
    op.create_index("ix_lab_sessions_student_id", "lab_sessions", ["student_id"])
    op.create_index("ix_lab_sessions_difficulty", "lab_sessions", ["difficulty"])
    op.create_index("ix_lab_sessions_status", "lab_sessions", ["status"])
    op.create_index("ix_lab_sessions_created_at", "lab_sessions", ["created_at"])
    op.create_index("ix_lab_sessions_completed_at", "lab_sessions", ["completed_at"])

    op.create_table(
        "validation_results",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("session_id", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("passed", sa.Boolean(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("checks_json", sa.JSON(), nullable=False),
        sa.Column("recommendations_json", sa.JSON(), nullable=False),
        sa.Column("raw_result_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["lab_sessions.session_id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id"),
    )
    op.create_index("ix_validation_results_session_id", "validation_results", ["session_id"])

    op.create_table(
        "recommendations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("session_id", sa.String(length=80), nullable=False),
        sa.Column("source", sa.String(length=80), nullable=False),
        sa.Column("fallback_used", sa.Boolean(), nullable=False),
        sa.Column("recommendations_json", sa.JSON(), nullable=False),
        sa.Column("raw_payload_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["lab_sessions.session_id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_recommendations_session_id", "recommendations", ["session_id"])


def downgrade() -> None:
    op.drop_index("ix_recommendations_session_id", table_name="recommendations")
    op.drop_table("recommendations")

    op.drop_index("ix_validation_results_session_id", table_name="validation_results")
    op.drop_table("validation_results")

    op.drop_index("ix_lab_sessions_completed_at", table_name="lab_sessions")
    op.drop_index("ix_lab_sessions_created_at", table_name="lab_sessions")
    op.drop_index("ix_lab_sessions_status", table_name="lab_sessions")
    op.drop_index("ix_lab_sessions_difficulty", table_name="lab_sessions")
    op.drop_index("ix_lab_sessions_student_id", table_name="lab_sessions")
    op.drop_table("lab_sessions")

    op.drop_index("ix_users_student_id", table_name="users")
    op.drop_index("ix_users_role", table_name="users")
    op.drop_table("users")