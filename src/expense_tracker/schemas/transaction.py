import uuid
from datetime import date

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from expense_tracker.schemas.base import AuditMixin, Base
from expense_tracker.schemas.tag import Tag


class TransactionTag(Base, AuditMixin):
    __tablename__ = "transaction_tags"

    transaction_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(
            "transactions.id",
            ondelete="CASCADE",
            name="fk_transaction_tags_transaction_id_transactions",
        ),
        primary_key=True,
        doc="Tagged transaction.",
    )
    tag_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(
            "tags.id", ondelete="CASCADE", name="fk_transaction_tags_tag_id_tags"
        ),
        primary_key=True,
        doc="Tag put on the transaction.",
    )


class Transaction(Base, AuditMixin):
    __tablename__ = "transactions"
    __table_args__ = (
        CheckConstraint("amount_minor <> 0", name="ck_transactions_amount_not_zero"),
        UniqueConstraint(
            "account_id", "import_hash", name="uq_transactions_account_id_import_hash"
        ),
        UniqueConstraint(
            "recurring_transaction_id",
            "booked_on",
            name="uq_transactions_recurring_transaction_id_booked_on",
        ),
        Index("ix_transactions_account_id_booked_on", "account_id", "booked_on"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, doc="Transaction id, uuid7."
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(
            "accounts.id",
            ondelete="RESTRICT",
            name="fk_transactions_account_id_accounts",
        ),
        doc="Account the transaction belongs to.",
    )
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(
            "categories.id",
            ondelete="RESTRICT",
            name="fk_transactions_category_id_categories",
        ),
        doc="Category of the transaction, null when uncategorised.",
    )
    amount_minor: Mapped[int] = mapped_column(
        BigInteger, doc="Signed amount in minor units, negative is an expense."
    )
    booked_on: Mapped[date] = mapped_column(Date, doc="Day the transaction happened.")
    description: Mapped[str] = mapped_column(Text, doc="Free text description.")
    import_hash: Mapped[str | None] = mapped_column(
        Text, doc="Hash of the CSV row, null when not imported."
    )
    recurring_transaction_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(
            "recurring_transactions.id",
            ondelete="SET NULL",
            name="fk_transactions_recurring_transaction_id_recurring_transactions",
        ),
        doc="Recurring rule that created the transaction, null otherwise.",
    )
    tags: Mapped[list[Tag]] = relationship(
        secondary="transaction_tags", lazy="selectin"
    )
