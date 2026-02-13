"""add lotw health columns

Revision ID: 20260212_01
Revises:
Create Date: 2026-02-12 17:45:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260212_01"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "users" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("users")}

    with op.batch_alter_table("users", schema=None) as batch_op:
        if "lotw_last_ok_at" not in existing_columns:
            batch_op.add_column(
                sa.Column("lotw_last_ok_at", sa.DateTime(timezone=True), nullable=True)
            )
        if "lotw_last_fail_at" not in existing_columns:
            batch_op.add_column(
                sa.Column("lotw_last_fail_at", sa.DateTime(timezone=True), nullable=True)
            )
        if "lotw_fail_count" not in existing_columns:
            batch_op.add_column(
                sa.Column(
                    "lotw_fail_count",
                    sa.Integer(),
                    nullable=False,
                    server_default="0",
                )
            )
        if "lotw_auth_state" not in existing_columns:
            batch_op.add_column(
                sa.Column(
                    "lotw_auth_state",
                    sa.String(length=32),
                    nullable=False,
                    server_default="unknown",
                )
            )
        if "lotw_last_fail_reason" not in existing_columns:
            batch_op.add_column(
                sa.Column("lotw_last_fail_reason", sa.String(length=255), nullable=True)
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "users" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("users")}

    with op.batch_alter_table("users", schema=None) as batch_op:
        if "lotw_last_fail_reason" in existing_columns:
            batch_op.drop_column("lotw_last_fail_reason")
        if "lotw_auth_state" in existing_columns:
            batch_op.drop_column("lotw_auth_state")
        if "lotw_fail_count" in existing_columns:
            batch_op.drop_column("lotw_fail_count")
        if "lotw_last_fail_at" in existing_columns:
            batch_op.drop_column("lotw_last_fail_at")
        if "lotw_last_ok_at" in existing_columns:
            batch_op.drop_column("lotw_last_ok_at")
