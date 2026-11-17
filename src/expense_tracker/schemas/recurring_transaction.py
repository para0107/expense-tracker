import uuid
from datetime import date

from sqlalchemy import BigInteger, CheckConstraint, Date, Enum, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from expense_tracker.models.recurring_transaction import RecurrenceCadence
from expense_tracker.schemas.base import AuditMixin, Base


class RecurringTransaction(Base, AuditMixin):
    __tablename__ = "recurring_transactions"
    __table_args__ = (
        CheckConstraint(
            "amount_minor <> 0", name="ck_recurring_transactions_amount_not_zero"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, doc="Recurring rule id, uuid7."
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(
            "accounts.id",
            ondelete="RESTRICT",
            name="fk_recurring_transactions_account_id_accounts",
        ),
        doc="Account the generated transactions are booked on.",
    )
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(
            "categories.id",
            ondelete="RESTRICT",
            name="fk_recurring_transactions_category_id_categories",
        ),
        doc="Category of the generated transactions, null when uncategorised.",
    )
    amount_minor: Mapped[int] = mapped_column(
        BigInteger, doc="Signed amount in minor units, negative is an expense."
    )
    description: Mapped[str] = mapped_column(
        Text, doc="Description of the generated transactions."
    )
    cadence: Mapped[RecurrenceCadence] = mapped_column(
        Enum(
            RecurrenceCadence,
            name="recurrence_cadence",
            values_callable=lambda members: [member.value for member in members],
        ),
        doc="How often the rule repeats: MONTHLY or WEEKLY.",
    )
    start_date: Mapped[date] = mapped_column(Date, doc="First day the rule applies.")
