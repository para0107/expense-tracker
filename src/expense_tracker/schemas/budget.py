import uuid
from datetime import date

from sqlalchemy import BigInteger, CheckConstraint, Date, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from expense_tracker.schemas.base import AuditMixin, Base


class Budget(Base, AuditMixin):
    __tablename__ = "budgets"
    __table_args__ = (
        CheckConstraint(
            "EXTRACT(DAY FROM month) = 1", name="ck_budgets_month_is_first_of_month"
        ),
        CheckConstraint("limit_minor > 0", name="ck_budgets_limit_minor_positive"),
        UniqueConstraint("category_id", "month", name="uq_budgets_category_id_month"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, doc="Budget id, uuid7.")
    category_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(
            "categories.id",
            ondelete="CASCADE",
            name="fk_budgets_category_id_categories",
        ),
        doc="Category the budget limits.",
    )
    month: Mapped[date] = mapped_column(Date, doc="First day of the budgeted month.")
    limit_minor: Mapped[int] = mapped_column(
        BigInteger, doc="Spending limit for the month in minor units."
    )
