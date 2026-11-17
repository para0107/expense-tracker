import uuid

from sqlalchemy import ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from expense_tracker.schemas.base import AuditMixin, Base


class Category(Base, AuditMixin):
    __tablename__ = "categories"
    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_categories_user_id_name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, doc="Category id, uuid7.")
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE", name="fk_categories_user_id_users"),
        doc="Owner of the category.",
    )
    name: Mapped[str] = mapped_column(Text, doc="Category name, unique per user.")
