"""enable_pgvector_extension

Revision ID: d8eb971ce9a8
Revises: 20240601_03
Create Date: 2026-09-04 14:45:54.892688
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = 'd8eb971ce9a8'
down_revision = '20240601_03'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")


def downgrade() -> None:
    op.execute("DROP EXTENSION IF EXISTS vector")
