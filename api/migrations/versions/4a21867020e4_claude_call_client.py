"""Who asked for each Claude call, so the daily limits can be counted.

Additive. The column is nullable because calls already logged were made before
anyone was being counted, and guessing a visitor for them would put made-up
attribution into the one table the product treats as the record of what
happened. They simply predate the limits.

The index carries the exact columns `budget.generates_today` filters on, in
that order: it runs on every generate, before anything else happens, and the
check that protects the budget should not itself be the slow part.

Revision ID: 4a21867020e4
Revises: 4c7ee4978b9a
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "4a21867020e4"
down_revision: Union[str, Sequence[str], None] = "4c7ee4978b9a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "claude_call", sa.Column("client", sa.String(length=32), nullable=True)
    )
    op.create_index(
        "ix_claude_call_client_day",
        "claude_call",
        ["client", "phase", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_claude_call_client_day", table_name="claude_call")
    op.drop_column("claude_call", "client")
