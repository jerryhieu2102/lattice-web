"""Private life events with provenance, optimistic versioning and minor-unit amounts."""

from alembic import op
import sqlalchemy as sa

revision = "0002_life_events"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "obligations", sa.Column("budget_only", sa.Boolean(), nullable=False, server_default=sa.false())
    )
    op.create_table(
        "life_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("actor_id", sa.String(36), sa.ForeignKey("actors.id"), nullable=False),
        sa.Column("event_type", sa.String(40), nullable=False),
        sa.Column("source", sa.String(20), nullable=False),
        sa.Column("raw_input", sa.Text(), nullable=False),
        sa.Column("title", sa.String(240), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("amount_minor", sa.BigInteger(), nullable=True),
        sa.Column("amount_min_minor", sa.BigInteger(), nullable=True),
        sa.Column("amount_max_minor", sa.BigInteger(), nullable=True),
        sa.Column("currency", sa.String(3), nullable=True),
        sa.Column("event_date", sa.Date(), nullable=True),
        sa.Column("expected_date", sa.Date(), nullable=True),
        sa.Column("date_window_start", sa.Date(), nullable=True),
        sa.Column("date_window_end", sa.Date(), nullable=True),
        sa.Column("counterparty", sa.String(120), nullable=True),
        sa.Column("category", sa.String(40), nullable=False),
        sa.Column("priority", sa.String(20), nullable=False),
        sa.Column("essentiality", sa.String(20), nullable=False),
        sa.Column("recurring", sa.Boolean(), nullable=False),
        sa.Column("recurrence_rule", sa.String(20), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("verification_status", sa.String(30), nullable=False),
        sa.Column(
            "linked_funding_source_id", sa.String(36), sa.ForeignKey("funding_sources.id"), nullable=True
        ),
        sa.Column("linked_obligation_id", sa.String(36), sa.ForeignKey("obligations.id"), nullable=True),
        sa.Column("linked_transaction_id", sa.String(36), nullable=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.CheckConstraint("amount_minor IS NULL OR amount_minor >= 0", name="life_amount_nonnegative"),
        sa.CheckConstraint("amount_min_minor IS NULL OR amount_min_minor >= 0", name="life_min_nonnegative"),
        sa.CheckConstraint(
            "amount_max_minor IS NULL OR amount_max_minor >= amount_min_minor", name="life_range_order"
        ),
    )
    op.create_index("ix_life_events_actor_id", "life_events", ["actor_id"])


def downgrade():
    op.drop_column("obligations", "budget_only")
    op.drop_index("ix_life_events_actor_id", table_name="life_events")
    op.drop_table("life_events")
