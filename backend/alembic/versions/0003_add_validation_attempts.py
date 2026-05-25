"""add validation attempt history

Revision ID: 0003_add_validation_attempts
Revises: 0002_add_user_auth_fields
Create Date: 2026-05-25
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0003_add_validation_attempts"
down_revision: Union[str, None] = "0002_add_user_auth_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "validation_attempts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("session_id", sa.String(length=80), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("passed", sa.Boolean(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("passed_checks", sa.Integer(), nullable=False),
        sa.Column("failed_checks", sa.Integer(), nullable=False),
        sa.Column("checks_json", sa.JSON(), nullable=False),
        sa.Column("recommendations_json", sa.JSON(), nullable=False),
        sa.Column("raw_result_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["lab_sessions.session_id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "session_id",
            "attempt_number",
            name="uq_validation_attempts_session_attempt",
        ),
    )
    op.create_index(
        "ix_validation_attempts_session_id",
        "validation_attempts",
        ["session_id"],
    )
    op.create_index(
        "ix_validation_attempts_created_at",
        "validation_attempts",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_validation_attempts_created_at", table_name="validation_attempts")
    op.drop_index("ix_validation_attempts_session_id", table_name="validation_attempts")
    op.drop_table("validation_attempts")
