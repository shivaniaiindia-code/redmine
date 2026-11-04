"""rename the built-in root admin account to admin@aiindia.com

Keeps the same user id, so its history, notifications and settings carry over.

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-04 19:30:00.000000
"""
from typing import Sequence, Union

from alembic import op


revision: str = '0005'
down_revision: Union[str, None] = '0004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

OLD, NEW = "admin@company.com", "admin@aiindia.com"


def _rename(old: str, new: str) -> None:
    for table in ("users", "employees"):
        op.execute(
            f"UPDATE {table} SET email = '{new}' WHERE email = '{old}' "
            f"AND NOT EXISTS (SELECT 1 FROM {table} t2 WHERE t2.email = '{new}')"
        )


def upgrade() -> None:
    _rename(OLD, NEW)


def downgrade() -> None:
    _rename(NEW, OLD)
