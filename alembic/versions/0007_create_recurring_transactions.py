"""create recurring transactions

Revision ID: 0007
Revises: 0006
Create Date: 2026-11-17

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

recurrence_cadence = postgresql.ENUM(
    "MONTHLY", "WEEKLY", name="recurrence_cadence", create_type=False
)


def upgrade() -> None:
    recurrence_cadence.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "recurring_transactions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("category_id", sa.Uuid(), nullable=True),
        sa.Column("amount_minor", sa.BigInteger(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("cadence", recurrence_cadence, nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "amount_minor <> 0", name="ck_recurring_transactions_amount_not_zero"
        ),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["accounts.id"],
            name="fk_recurring_transactions_account_id_accounts",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["categories.id"],
            name="fk_recurring_transactions_category_id_categories",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_recurring_transactions")),
    )
    op.create_foreign_key(
        "fk_transactions_recurring_transaction_id_recurring_transactions",
        "transactions",
        "recurring_transactions",
        ["recurring_transaction_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_transactions_recurring_transaction_id_recurring_transactions",
        "transactions",
        type_="foreignkey",
    )
    op.drop_table("recurring_transactions")
    recurrence_cadence.drop(op.get_bind(), checkfirst=True)
