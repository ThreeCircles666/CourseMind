"""Add document_chunks table for text embeddings

Revision ID: 7bbcb363bbc6
Revises: d8eb971ce9a8
Create Date: 2026-09-04 17:15:36.238612
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import VECTOR


revision = '7bbcb363bbc6'
down_revision = 'd8eb971ce9a8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create document_chunks table
    op.create_table(
        'document_chunks',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('document_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('chunk_index', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('page_number', sa.Integer(), nullable=True),
        sa.Column('title_path', postgresql.ARRAY(sa.Text()), nullable=False, server_default=sa.text("'{}'::text[]")),
        sa.Column('start_char', sa.Integer(), nullable=False),
        sa.Column('end_char', sa.Integer(), nullable=False),
        sa.Column('embedding_model', sa.String(length=100), nullable=False),
        sa.Column('embedding_dimension', sa.Integer(), nullable=False),
        sa.Column('embedding', VECTOR(1024), nullable=False),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint('chunk_index >= 0', name='ck_document_chunks_chunk_index_nonnegative'),
        sa.CheckConstraint('length(btrim(content)) > 0', name='ck_document_chunks_content_nonempty'),
        sa.CheckConstraint('page_number IS NULL OR page_number > 0', name='ck_document_chunks_page_number_positive'),
        sa.CheckConstraint('start_char >= 0', name='ck_document_chunks_start_char_nonnegative'),
        sa.CheckConstraint('end_char > start_char', name='ck_document_chunks_char_range_valid'),
        sa.CheckConstraint('embedding_dimension = 1024', name='ck_document_chunks_embedding_dimension'),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], name='fk_document_chunks_document_id_documents', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name='pk_document_chunks')
    )

    # Create indexes
    op.create_index('ix_document_chunks_document_model', 'document_chunks', ['document_id', 'embedding_model'], unique=False)
    op.create_index('uq_document_chunks_document_index_model', 'document_chunks', ['document_id', 'chunk_index', 'embedding_model'], unique=True)


def downgrade() -> None:
    # Drop indexes
    op.drop_index('uq_document_chunks_document_index_model', table_name='document_chunks')
    op.drop_index('ix_document_chunks_document_model', table_name='document_chunks')

    # Drop table
    op.drop_table('document_chunks')
