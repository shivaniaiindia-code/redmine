"""add access-approval columns to users

Super Admin / Company Management accounts stay approved; every other
existing account and every new self sign-up starts PENDING.

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-04 18:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0004'
down_revision: Union[str, None] = '0003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _columns(table: str) -> set[str]:
    return {c["name"] for c in sa.inspect(op.get_bind()).get_columns(table)}


def upgrade() -> None:
    cols = _columns('users')
    with op.batch_alter_table('users', schema=None) as batch_op:
        if 'approval_status' not in cols:
            batch_op.add_column(sa.Column('approval_status', sa.String(length=20),
                                          nullable=False, server_default='APPROVED'))
        if 'reviewed_by' not in cols:
            batch_op.add_column(sa.Column('reviewed_by', sa.String(length=255), nullable=True))
        if 'reviewed_at' not in cols:
            batch_op.add_column(sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True))

    if 'approval_status' not in cols:
        # Only company-wide administrators stay approved. Every other existing
        # account (e.g. self sign-ups made before approval existed) must be
        # reviewed in Administration > Access Requests before it can see data.
        op.execute(
            "UPDATE users SET approval_status = 'PENDING' WHERE role_id NOT IN "
            "(SELECT id FROM roles WHERE name IN ('SUPER_ADMIN', 'COMPANY_MANAGEMENT'))"
        )


def downgrade() -> None:
    cols = _columns('users')
    with op.batch_alter_table('users', schema=None) as batch_op:
        for name in ('reviewed_at', 'reviewed_by', 'approval_status'):
            if name in cols:
                batch_op.drop_column(name)
