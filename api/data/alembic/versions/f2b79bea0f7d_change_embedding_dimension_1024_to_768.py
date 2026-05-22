"""change embedding dimension 1024 to 768
Revision ID: f2b79bea0f7d
Revises: 6a6d4579355d
Create Date: 2026-05-22 10:25:17.221738
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision: str = 'f2b79bea0f7d'
down_revision: Union[str, Sequence[str], None] = '6a6d4579355d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("DELETE FROM rag.document_chunks")
    op.alter_column(
        'document_chunks', 'embedding',
        existing_type=Vector(1024),
        type_=Vector(768),
        existing_nullable=True,
        schema='rag'
    )


def downgrade() -> None:
    op.execute("DELETE FROM rag.document_chunks")
    op.alter_column(
        'document_chunks', 'embedding',
        existing_type=Vector(768),
        type_=Vector(1024),
        existing_nullable=True,
        schema='rag'
    )
