"""alert routing, scheduled emails, email retry

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-03 18:33:41.548667
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0002'
down_revision: Union[str, None] = '0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

CONFIG_COLUMNS = [
    sa.Column('notify_assignee', sa.Boolean(), server_default=sa.text('0'), nullable=False),
    sa.Column('notify_project_manager', sa.Boolean(), server_default=sa.text('0'), nullable=False),
    sa.Column('daily_digest_enabled', sa.Boolean(), server_default=sa.text('1'), nullable=False),
    sa.Column('weekly_report_enabled', sa.Boolean(), server_default=sa.text('1'), nullable=False),
    sa.Column('digest_hour', sa.Integer(), server_default=sa.text('9'), nullable=False),
    sa.Column('weekly_report_weekday', sa.Integer(), server_default=sa.text('0'), nullable=False),
]


def _has_table(name: str) -> bool:
    return name in sa.inspect(op.get_bind()).get_table_names()


def _columns(table: str) -> set[str]:
    return {c["name"] for c in sa.inspect(op.get_bind()).get_columns(table)}


def upgrade() -> None:
    # Idempotent: a database touched by an older create_all() may already have parts of this.
    if not _has_table('scheduled_email_runs'):
        op.create_table(
            'scheduled_email_runs',
            sa.Column('id', sa.String(length=36), nullable=False),
            sa.Column('kind', sa.String(length=30), nullable=False),
            sa.Column('period_key', sa.String(length=30), nullable=False),
            sa.Column('status', sa.String(length=20), nullable=False),
            sa.Column('sent_count', sa.Integer(), nullable=False),
            sa.Column('recipient_count', sa.Integer(), nullable=False),
            sa.Column('detail', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('kind', 'period_key', name='uq_scheduled_email_run'),
        )

    existing = _columns('alert_recipient_config')
    missing = [c for c in CONFIG_COLUMNS if c.name not in existing]
    if missing:
        with op.batch_alter_table('alert_recipient_config', schema=None) as batch_op:
            for col in missing:
                batch_op.add_column(col.copy())

    if 'next_retry_at' not in _columns('notification_deliveries'):
        with op.batch_alter_table('notification_deliveries', schema=None) as batch_op:
            batch_op.add_column(sa.Column('next_retry_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('notification_deliveries', schema=None) as batch_op:
        batch_op.drop_column('next_retry_at')

    with op.batch_alter_table('alert_recipient_config', schema=None) as batch_op:
        for col in reversed(CONFIG_COLUMNS):
            batch_op.drop_column(col.name)

    op.drop_table('scheduled_email_runs')
