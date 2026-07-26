"""add basic_udi_di.applicable_legislation (MDR/MDD/AIMDD, legacy support)

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-07-25
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from eudamed_tool.models import ApplicableLegislation

revision: str = "f6a7b8c9d0e1"
down_revision: Union[str, Sequence[str], None] = "e5f6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_enum = sa.Enum(ApplicableLegislation, name="applicable_legislation_enum",
                values_callable=lambda e: [m.value for m in e])


def upgrade() -> None:
    _enum.create(op.get_bind(), checkfirst=True)
    op.add_column("basic_udi_di", sa.Column(
        "applicable_legislation", _enum, nullable=False, server_default="MDR"))


def downgrade() -> None:
    op.drop_column("basic_udi_di", "applicable_legislation")
    _enum.drop(op.get_bind(), checkfirst=True)
