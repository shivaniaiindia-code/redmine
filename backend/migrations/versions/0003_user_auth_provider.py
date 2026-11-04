"""add auth_provider to users

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-04 12:50:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0003'
down_revision: Union[str, None] = '0002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _columns(table: str) -> set[str]:
    return {c["name"] for c in sa.inspect(op.get_bind()).get_columns(table)}


def upgrade() -> None:
    if 'auth_provider' not in _columns('users'):
        with op.batch_alter_table('users', schema=None) as batch_op:
            batch_op.add_column(
                sa.Column('auth_provider', sa.String(length=50), nullable=True)
            )


def downgrade() -> None:
    if 'auth_provider' in _columns('users'):
        with op.batch_alter_table('users', schema=None) as batch_op:
            batch_op.drop_column('auth_provider')

