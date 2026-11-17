import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from expense_tracker.schemas.base import AuditMixin, Base


class Account(Base, AuditMixin):
    __tablename__ = "accounts"
    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_accounts_user_id_name"),
        CheckConstraint("currency ~ '^[A-Z]{3}$'", name="ck_accounts_currency_format"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, doc="Account id, uuid7.")
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE", name="fk_accounts_user_id_users"),
        doc="Owner of the account.",
    )
    name: Mapped[str] = mapped_column(Text, doc="Account name, unique per user.")
    currency: Mapped[str] = mapped_column(
        Text, doc="ISO 4217 currency code, three uppercase letters."
    )
