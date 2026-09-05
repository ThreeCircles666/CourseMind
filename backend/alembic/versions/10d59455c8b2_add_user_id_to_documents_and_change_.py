"""add_user_id_to_documents_and_change_sha256_unique_constraint

Revision ID: 10d59455c8b2
Revises: 7bbcb363bbc6
Create Date: 2024-09-05

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '10d59455c8b2'
down_revision = '7bbcb363bbc6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add user_id column (nullable to allow existing documents)
    op.add_column('documents', sa.Column('user_id', sa.Integer(), nullable=True))

    # Add foreign key to users table
    op.create_foreign_key(
        'fk_documents_user_id',
        'documents',
        'users',
        ['user_id'],
        ['id'],
        ondelete='RESTRICT'
    )

    # Create index for user queries
    op.create_index(
        'ix_documents_user_id',
        'documents',
        ['user_id'],
        unique=False
    )

    # Drop old global sha256 unique constraint
    op.drop_constraint('uq_documents_sha256', 'documents', type_='unique')

    # Create new composite unique constraint: per-user sha256 uniqueness
    # NULL user_id documents are allowed (historical records)
    op.create_unique_constraint(
        'uq_documents_user_sha256',
        'documents',
        ['user_id', 'sha256']
    )


def downgrade() -> None:
    # Drop composite unique constraint
    op.drop_constraint('uq_documents_user_sha256', 'documents', type_='unique')

    # Restore global sha256 unique constraint
    # WARNING: This may fail if multiple users have same sha256
    op.create_unique_constraint('uq_documents_sha256', 'documents', ['sha256'])

    # Drop index
    op.drop_index('ix_documents_user_id', table_name='documents')

    # Drop foreign key
    op.drop_constraint('fk_documents_user_id', 'documents', type_='foreignkey')

    # Drop user_id column
    op.drop_column('documents', 'user_id')
