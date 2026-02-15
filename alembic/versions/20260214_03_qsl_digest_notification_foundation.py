"""add qsl digest notification foundation tables

Revision ID: 20260214_03
Revises: 20260213_02
Create Date: 2026-02-14 11:05:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260214_03"
down_revision: Union[str, None] = "20260213_02"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_names(inspector: sa.Inspector) -> set[str]:
    return set(inspector.get_table_names())


def _index_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    return {index["name"] for index in inspector.get_indexes(table_name)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = _table_names(inspector)

    if "users" in table_names:
        existing_columns = {column["name"] for column in inspector.get_columns("users")}
        with op.batch_alter_table("users", schema=None) as batch_op:
            if "email_verified_at" not in existing_columns:
                batch_op.add_column(
                    sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True)
                )
            if "timezone" not in existing_columns:
                batch_op.add_column(
                    sa.Column(
                        "timezone",
                        sa.String(length=64),
                        nullable=False,
                        server_default="UTC",
                    )
                )
            if "locale" not in existing_columns:
                batch_op.add_column(sa.Column("locale", sa.String(length=16), nullable=True))

    if "notification_preferences" not in table_names:
        op.create_table(
            "notification_preferences",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column(
                "qsl_digest_enabled",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            ),
            sa.Column(
                "qsl_digest_time_local",
                sa.Time(),
                nullable=False,
                server_default="08:00:00",
            ),
            sa.Column(
                "qsl_digest_frequency",
                sa.String(length=32),
                nullable=False,
                server_default="daily",
            ),
            sa.Column(
                "fallback_to_email",
                sa.Boolean(),
                nullable=False,
                server_default=sa.true(),
            ),
            sa.Column("quiet_hours_start_local", sa.Time(), nullable=True),
            sa.Column("quiet_hours_end_local", sa.Time(), nullable=True),
            sa.Column("last_digest_cursor_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
        )

    if "web_push_subscriptions" not in table_names:
        op.create_table(
            "web_push_subscriptions",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("endpoint", sa.Text(), nullable=False),
            sa.Column("p256dh_key", sa.Text(), nullable=False),
            sa.Column("auth_key", sa.Text(), nullable=False),
            sa.Column(
                "status",
                sa.String(length=32),
                nullable=False,
                server_default="active",
            ),
            sa.Column("user_agent", sa.Text(), nullable=True),
            sa.Column("platform", sa.String(length=64), nullable=True),
            sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_failure_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column(
                "failure_count",
                sa.Integer(),
                nullable=False,
                server_default="0",
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
        )

    if "qsl_digest_batches" not in table_names:
        op.create_table(
            "qsl_digest_batches",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("digest_date", sa.Date(), nullable=False),
            sa.Column("window_start_utc", sa.DateTime(timezone=True), nullable=False),
            sa.Column("window_end_utc", sa.DateTime(timezone=True), nullable=False),
            sa.Column(
                "qsl_count",
                sa.Integer(),
                nullable=False,
                server_default="0",
            ),
            sa.Column("payload_json", sa.JSON(), nullable=False),
            sa.Column(
                "generated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
        )

    if "notification_deliveries" not in table_names:
        op.create_table(
            "notification_deliveries",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column(
                "digest_batch_id",
                sa.Integer(),
                sa.ForeignKey("qsl_digest_batches.id"),
                nullable=True,
            ),
            sa.Column(
                "type",
                sa.String(length=32),
                nullable=False,
                server_default="qsl_digest",
            ),
            sa.Column("channel", sa.String(length=32), nullable=False),
            sa.Column(
                "status",
                sa.String(length=32),
                nullable=False,
                server_default="queued",
            ),
            sa.Column("provider_message_id", sa.String(length=255), nullable=True),
            sa.Column("error_code", sa.String(length=128), nullable=True),
            sa.Column("error_detail", sa.Text(), nullable=True),
            sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
        )

    # Refresh table/index metadata now that tables may exist.
    inspector = sa.inspect(bind)

    if "notification_preferences" in _table_names(inspector):
        pref_indexes = _index_names(inspector, "notification_preferences")
        if "ix_notification_preferences_user_id" not in pref_indexes:
            op.create_index(
                "ix_notification_preferences_user_id",
                "notification_preferences",
                ["user_id"],
                unique=True,
            )

    if "web_push_subscriptions" in _table_names(inspector):
        push_indexes = _index_names(inspector, "web_push_subscriptions")
        if "ix_web_push_subscriptions_user_id" not in push_indexes:
            op.create_index(
                "ix_web_push_subscriptions_user_id",
                "web_push_subscriptions",
                ["user_id"],
                unique=False,
            )
        if "ix_web_push_subscriptions_endpoint" not in push_indexes:
            op.create_index(
                "ix_web_push_subscriptions_endpoint",
                "web_push_subscriptions",
                ["endpoint"],
                unique=True,
            )

    if "qsl_digest_batches" in _table_names(inspector):
        digest_indexes = _index_names(inspector, "qsl_digest_batches")
        if "ix_qsl_digest_batches_user_id" not in digest_indexes:
            op.create_index(
                "ix_qsl_digest_batches_user_id",
                "qsl_digest_batches",
                ["user_id"],
                unique=False,
            )
        if "ix_qsl_digest_batches_user_digest_date" not in digest_indexes:
            op.create_index(
                "ix_qsl_digest_batches_user_digest_date",
                "qsl_digest_batches",
                ["user_id", "digest_date"],
                unique=True,
            )

    if "notification_deliveries" in _table_names(inspector):
        delivery_indexes = _index_names(inspector, "notification_deliveries")
        if "ix_notification_deliveries_user_id" not in delivery_indexes:
            op.create_index(
                "ix_notification_deliveries_user_id",
                "notification_deliveries",
                ["user_id"],
                unique=False,
            )
        if "ix_notification_deliveries_digest_batch_id" not in delivery_indexes:
            op.create_index(
                "ix_notification_deliveries_digest_batch_id",
                "notification_deliveries",
                ["digest_batch_id"],
                unique=False,
            )
        if "ix_notification_deliveries_user_digest_channel" not in delivery_indexes:
            op.create_index(
                "ix_notification_deliveries_user_digest_channel",
                "notification_deliveries",
                ["user_id", "digest_batch_id", "channel"],
                unique=True,
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = _table_names(inspector)

    if "notification_deliveries" in table_names:
        delivery_indexes = _index_names(inspector, "notification_deliveries")
        if "ix_notification_deliveries_user_digest_channel" in delivery_indexes:
            op.drop_index(
                "ix_notification_deliveries_user_digest_channel",
                table_name="notification_deliveries",
            )
        if "ix_notification_deliveries_digest_batch_id" in delivery_indexes:
            op.drop_index(
                "ix_notification_deliveries_digest_batch_id",
                table_name="notification_deliveries",
            )
        if "ix_notification_deliveries_user_id" in delivery_indexes:
            op.drop_index(
                "ix_notification_deliveries_user_id",
                table_name="notification_deliveries",
            )
        op.drop_table("notification_deliveries")

    inspector = sa.inspect(bind)
    table_names = _table_names(inspector)
    if "qsl_digest_batches" in table_names:
        digest_indexes = _index_names(inspector, "qsl_digest_batches")
        if "ix_qsl_digest_batches_user_digest_date" in digest_indexes:
            op.drop_index(
                "ix_qsl_digest_batches_user_digest_date",
                table_name="qsl_digest_batches",
            )
        if "ix_qsl_digest_batches_user_id" in digest_indexes:
            op.drop_index(
                "ix_qsl_digest_batches_user_id",
                table_name="qsl_digest_batches",
            )
        op.drop_table("qsl_digest_batches")

    inspector = sa.inspect(bind)
    table_names = _table_names(inspector)
    if "web_push_subscriptions" in table_names:
        push_indexes = _index_names(inspector, "web_push_subscriptions")
        if "ix_web_push_subscriptions_endpoint" in push_indexes:
            op.drop_index(
                "ix_web_push_subscriptions_endpoint",
                table_name="web_push_subscriptions",
            )
        if "ix_web_push_subscriptions_user_id" in push_indexes:
            op.drop_index(
                "ix_web_push_subscriptions_user_id",
                table_name="web_push_subscriptions",
            )
        op.drop_table("web_push_subscriptions")

    inspector = sa.inspect(bind)
    table_names = _table_names(inspector)
    if "notification_preferences" in table_names:
        pref_indexes = _index_names(inspector, "notification_preferences")
        if "ix_notification_preferences_user_id" in pref_indexes:
            op.drop_index(
                "ix_notification_preferences_user_id",
                table_name="notification_preferences",
            )
        op.drop_table("notification_preferences")

    inspector = sa.inspect(bind)
    if "users" in _table_names(inspector):
        existing_columns = {column["name"] for column in inspector.get_columns("users")}
        with op.batch_alter_table("users", schema=None) as batch_op:
            if "locale" in existing_columns:
                batch_op.drop_column("locale")
            if "timezone" in existing_columns:
                batch_op.drop_column("timezone")
            if "email_verified_at" in existing_columns:
                batch_op.drop_column("email_verified_at")
