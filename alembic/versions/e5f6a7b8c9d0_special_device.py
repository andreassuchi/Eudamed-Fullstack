"""add basic_udi_di.special_device (MDR special device type)

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-07-25
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from eudamed_tool.models import SpecialDeviceType

revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, Sequence[str], None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_enum = sa.Enum(SpecialDeviceType, name="special_device_type_enum",
                values_callable=lambda e: [m.value for m in e])


def upgrade() -> None:
    _enum.create(op.get_bind(), checkfirst=True)
    op.add_column("basic_udi_di", sa.Column("special_device", _enum, nullable=True))


def downgrade() -> None:
    op.drop_column("basic_udi_di", "special_device")
    _enum.drop(op.get_bind(), checkfirst=True)
