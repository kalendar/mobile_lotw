"""add notification email preference fields

Revision ID: 20260215_04
Revises: 20260214_03
Create Date: 2026-02-15 11:20:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260215_04"
down_revision: Union[str, None] = "20260214_03"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())

    if "notification_preferences" not in table_names:
        return

    existing_columns = {
        column["name"] for column in inspector.get_columns("notification_preferences")
    }

    with op.batch_alter_table("notification_preferences", schema=None) as batch_op:
        if "use_account_email_for_notifications" not in existing_columns:
            batch_op.add_column(
                sa.Column(
                    "use_account_email_for_notifications",
                    sa.Boolean(),
                    nullable=False,
                    server_default=sa.true(),
                )
            )
        if "notification_email" not in existing_columns:
            batch_op.add_column(
                sa.Column("notification_email", sa.String(length=255), nullable=True)
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())
    if "notification_preferences" not in table_names:
        return

    existing_columns = {
        column["name"] for column in inspector.get_columns("notification_preferences")
    }

    with op.batch_alter_table("notification_preferences", schema=None) as batch_op:
        if "notification_email" in existing_columns:
            batch_op.drop_column("notification_email")
        if "use_account_email_for_notifications" in existing_columns:
            batch_op.drop_column("use_account_email_for_notifications")
