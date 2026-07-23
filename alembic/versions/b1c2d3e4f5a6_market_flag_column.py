"""add market_country.original_placed_on_market (universal profile)

Revision ID: b1c2d3e4f5a6
Revises: aa520d371334
Create Date: 2026-07-23
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b1c2d3e4f5a6"
down_revision: Union[str, Sequence[str], None] = "aa520d371334"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "market_country",
        sa.Column("original_placed_on_market", sa.Boolean(), nullable=False,
                  server_default=sa.false()),
    )
    # backfill with the previous derivation rule (DE = originally placed)
    op.execute("UPDATE market_country SET original_placed_on_market = (country_code = 'DE')")


def downgrade() -> None:
    op.drop_column("market_country", "original_placed_on_market")
