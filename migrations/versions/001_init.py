"""init

Revision ID: 001_init
Revises: 
Create Date: 2026-01-15 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "001_init"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "videos",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("raw_object_key", sa.String(length=1024), nullable=False),
        sa.Column("processed_object_key", sa.String(length=1024), nullable=True),
        sa.Column("cover_object_key", sa.String(length=1024), nullable=True),
        sa.Column("duration_sec", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
    )
    op.create_index("ix_videos_user_id", "videos", ["user_id"], unique=False)
    op.create_index("ix_videos_status", "videos", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_videos_status", table_name="videos")
    op.drop_index("ix_videos_user_id", table_name="videos")
    op.drop_table("videos")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
