"""add billing, sync status, and performance indexes

Revision ID: 20260213_02
Revises: 20260212_01
Create Date: 2026-02-13 10:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.exc import ProgrammingError


# revision identifiers, used by Alembic.
revision: str = "20260213_02"
down_revision: Union[str, None] = "20260212_01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _index_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    return {index["name"] for index in inspector.get_indexes(table_name)}


def _is_duplicate_table_error(error: ProgrammingError) -> bool:
    # Postgres duplicate table SQLSTATE.
    code = getattr(getattr(error, "orig", None), "sqlstate", None)
    return code == "42P07"


def _create_stripe_events_table_if_missing(bind, inspector: sa.Inspector) -> None:
    if inspector.has_table("stripe_events"):
        return

    try:
        op.create_table(
            "stripe_events",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("event_id", sa.String(length=255), nullable=False),
            sa.Column("event_type", sa.String(length=255), nullable=False),
            sa.Column(
                "status",
                sa.String(length=32),
                nullable=False,
                server_default="received",
            ),
            sa.Column("payload", sa.JSON(), nullable=True),
            sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        )
    except ProgrammingError as error:
        # Allow concurrent/previous creation to pass safely.
        if not _is_duplicate_table_error(error):
            raise

    refreshed_inspector = sa.inspect(bind)
    stripe_indexes = _index_names(refreshed_inspector, "stripe_events")
    if "ix_stripe_events_event_id" not in stripe_indexes:
        op.create_index(
            "ix_stripe_events_event_id",
            "stripe_events",
            ["event_id"],
            unique=True,
        )


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "users" in inspector.get_table_names():
        existing_columns = {
            column["name"] for column in inspector.get_columns("users")
        }
        with op.batch_alter_table("users", schema=None) as batch_op:
            if "email" not in existing_columns:
                batch_op.add_column(sa.Column("email", sa.String(), nullable=True))
            if "qso_sync_status" not in existing_columns:
                batch_op.add_column(
                    sa.Column(
                        "qso_sync_status",
                        sa.String(length=32),
                        nullable=False,
                        server_default="idle",
                    )
                )
            if "qso_sync_started_at" not in existing_columns:
                batch_op.add_column(
                    sa.Column("qso_sync_started_at", sa.DateTime(timezone=True), nullable=True)
                )
            if "qso_sync_finished_at" not in existing_columns:
                batch_op.add_column(
                    sa.Column("qso_sync_finished_at", sa.DateTime(timezone=True), nullable=True)
                )
            if "qso_sync_last_error" not in existing_columns:
                batch_op.add_column(
                    sa.Column("qso_sync_last_error", sa.String(length=512), nullable=True)
                )
            if "plan_tier" not in existing_columns:
                batch_op.add_column(
                    sa.Column(
                        "plan_tier",
                        sa.String(length=32),
                        nullable=False,
                        server_default="free",
                    )
                )
            if "stripe_customer_id" not in existing_columns:
                batch_op.add_column(
                    sa.Column("stripe_customer_id", sa.String(length=255), nullable=True)
                )
            if "stripe_subscription_id" not in existing_columns:
                batch_op.add_column(
                    sa.Column("stripe_subscription_id", sa.String(length=255), nullable=True)
                )
            if "subscription_status" not in existing_columns:
                batch_op.add_column(
                    sa.Column(
                        "subscription_status",
                        sa.String(length=32),
                        nullable=False,
                        server_default="inactive",
                    )
                )
            if "subscription_current_period_end" not in existing_columns:
                batch_op.add_column(
                    sa.Column(
                        "subscription_current_period_end",
                        sa.DateTime(timezone=True),
                        nullable=True,
                    )
                )
            if "entitlement_expires_at" not in existing_columns:
                batch_op.add_column(
                    sa.Column("entitlement_expires_at", sa.DateTime(timezone=True), nullable=True)
                )

        user_indexes = _index_names(inspector, "users")
        if "ix_users_op" not in user_indexes:
            op.create_index("ix_users_op", "users", ["op"], unique=False)
        if "ix_users_stripe_customer_id" not in user_indexes:
            op.create_index(
                "ix_users_stripe_customer_id",
                "users",
                ["stripe_customer_id"],
                unique=False,
            )
        if "ix_users_stripe_subscription_id" not in user_indexes:
            op.create_index(
                "ix_users_stripe_subscription_id",
                "users",
                ["stripe_subscription_id"],
                unique=False,
            )
        if "ix_users_subscription_status" not in user_indexes:
            op.create_index(
                "ix_users_subscription_status",
                "users",
                ["subscription_status"],
                unique=False,
            )

    if "qso_reports" in inspector.get_table_names():
        qso_indexes = _index_names(inspector, "qso_reports")
        if "ix_qso_reports_user_rxqsl" not in qso_indexes:
            op.create_index(
                "ix_qso_reports_user_rxqsl",
                "qso_reports",
                ["user_id", "app_lotw_rxqsl"],
                unique=False,
            )
        if "ix_qso_reports_user_call" not in qso_indexes:
            op.create_index(
                "ix_qso_reports_user_call",
                "qso_reports",
                ["user_id", "call"],
                unique=False,
            )
        if "ix_qso_reports_user_qso_timestamp" not in qso_indexes:
            op.create_index(
                "ix_qso_reports_user_qso_timestamp",
                "qso_reports",
                ["user_id", "app_lotw_qso_timestamp"],
                unique=False,
            )
        if "ix_qso_reports_user_lat_long" not in qso_indexes:
            op.create_index(
                "ix_qso_reports_user_lat_long",
                "qso_reports",
                ["user_id", "latitude", "longitude"],
                unique=False,
            )

    _create_stripe_events_table_if_missing(bind, inspector)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "stripe_events" in inspector.get_table_names():
        stripe_indexes = _index_names(inspector, "stripe_events")
        if "ix_stripe_events_event_id" in stripe_indexes:
            op.drop_index("ix_stripe_events_event_id", table_name="stripe_events")
        op.drop_table("stripe_events")

    if "qso_reports" in inspector.get_table_names():
        qso_indexes = _index_names(inspector, "qso_reports")
        if "ix_qso_reports_user_lat_long" in qso_indexes:
            op.drop_index("ix_qso_reports_user_lat_long", table_name="qso_reports")
        if "ix_qso_reports_user_qso_timestamp" in qso_indexes:
            op.drop_index(
                "ix_qso_reports_user_qso_timestamp", table_name="qso_reports"
            )
        if "ix_qso_reports_user_call" in qso_indexes:
            op.drop_index("ix_qso_reports_user_call", table_name="qso_reports")
        if "ix_qso_reports_user_rxqsl" in qso_indexes:
            op.drop_index("ix_qso_reports_user_rxqsl", table_name="qso_reports")

    if "users" in inspector.get_table_names():
        user_indexes = _index_names(inspector, "users")
        if "ix_users_subscription_status" in user_indexes:
            op.drop_index("ix_users_subscription_status", table_name="users")
        if "ix_users_stripe_subscription_id" in user_indexes:
            op.drop_index("ix_users_stripe_subscription_id", table_name="users")
        if "ix_users_stripe_customer_id" in user_indexes:
            op.drop_index("ix_users_stripe_customer_id", table_name="users")
        if "ix_users_op" in user_indexes:
            op.drop_index("ix_users_op", table_name="users")

        existing_columns = {
            column["name"] for column in inspector.get_columns("users")
        }
        with op.batch_alter_table("users", schema=None) as batch_op:
            if "entitlement_expires_at" in existing_columns:
                batch_op.drop_column("entitlement_expires_at")
            if "subscription_current_period_end" in existing_columns:
                batch_op.drop_column("subscription_current_period_end")
            if "subscription_status" in existing_columns:
                batch_op.drop_column("subscription_status")
            if "stripe_subscription_id" in existing_columns:
                batch_op.drop_column("stripe_subscription_id")
            if "stripe_customer_id" in existing_columns:
                batch_op.drop_column("stripe_customer_id")
            if "plan_tier" in existing_columns:
                batch_op.drop_column("plan_tier")
            if "qso_sync_last_error" in existing_columns:
                batch_op.drop_column("qso_sync_last_error")
            if "qso_sync_finished_at" in existing_columns:
                batch_op.drop_column("qso_sync_finished_at")
            if "qso_sync_started_at" in existing_columns:
                batch_op.drop_column("qso_sync_started_at")
            if "qso_sync_status" in existing_columns:
                batch_op.drop_column("qso_sync_status")
            if "email" in existing_columns:
                batch_op.drop_column("email")
