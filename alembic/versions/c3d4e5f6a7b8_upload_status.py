"""add EUDAMED upload-status columns to basic_udi_di and device

Revision ID: c3d4e5f6a7b8
Revises: b1c2d3e4f5a6
Create Date: 2026-07-24
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, Sequence[str], None] = "b1c2d3e4f5a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_COLUMNS = [
    ("upload_status", sa.String(length=20), {"nullable": False, "server_default": "NOT_UPLOADED"}),
    ("uploaded_at", sa.DateTime(timezone=True), {"nullable": True}),
    ("upload_response_code", sa.String(length=40), {"nullable": True}),
    ("upload_snapshot_hash", sa.String(length=64), {"nullable": True}),
    ("upload_message", sa.Text(), {"nullable": True}),
]


def upgrade() -> None:
    for table in ("basic_udi_di", "device"):
        for name, type_, kw in _COLUMNS:
            op.add_column(table, sa.Column(name, type_, **kw))


def downgrade() -> None:
    for table in ("basic_udi_di", "device"):
        for name, _type, _kw in _COLUMNS:
            op.drop_column(table, name)
