"""add xml_generation_job.output_dir and files (multi-file upload packages)

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-07-24
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, Sequence[str], None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_JSON = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    op.add_column("xml_generation_job", sa.Column("output_dir", sa.String(length=500), nullable=True))
    op.add_column("xml_generation_job", sa.Column("files", _JSON, nullable=True))


def downgrade() -> None:
    op.drop_column("xml_generation_job", "files")
    op.drop_column("xml_generation_job", "output_dir")
