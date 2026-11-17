import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from expense_tracker.schemas.base import AuditMixin, Base


class User(Base, AuditMixin):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, doc="User id, uuid7.")
    email: Mapped[str] = mapped_column(
        Text, unique=True, doc="Login email, stored lowercase."
    )
    password_hash: Mapped[str] = mapped_column(Text, doc="Argon2id password hash.")


class RefreshSession(Base, AuditMixin):
    __tablename__ = "refresh_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, doc="Refresh session id, uuid7."
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(
            "users.id", ondelete="CASCADE", name="fk_refresh_sessions_user_id_users"
        ),
        doc="Owner of the session.",
    )
    family_id: Mapped[uuid.UUID] = mapped_column(
        index=True, doc="Shared by every token rotated from one login."
    )
    token_hash: Mapped[str] = mapped_column(
        Text, unique=True, doc="SHA-256 hex of the refresh token."
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), doc="When the refresh token stops being valid."
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), doc="When the token was revoked, null if active."
    )
