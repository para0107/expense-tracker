import logging
import uuid
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from expense_tracker.exceptions.app_error import AppError
from expense_tracker.exceptions.error_codes import AppErrorCode
from expense_tracker.schemas import RefreshSession

logger = logging.getLogger(__name__)


class RefreshSessionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_refresh_session(
        self, refresh_session: RefreshSession
    ) -> RefreshSession:
        """
        Insert the refresh session as a new row and return it.
        """
        try:
            self._session.add(refresh_session)
            await self._session.flush()
            return refresh_session
        except SQLAlchemyError as error:
            logger.exception(
                "Could not create refresh_session_id=%s.", refresh_session.id
            )
            raise AppError(AppErrorCode.DATABASE_ERROR) from error

    async def get_refresh_session_by_token_hash_for_update(
        self, token_hash: str
    ) -> RefreshSession | None:
        """
        Return the session with this token hash and lock its row, so concurrent
        refreshes of one token run one after the other.
        """
        try:
            statement = (
                select(RefreshSession)
                .where(RefreshSession.token_hash == token_hash)
                .with_for_update()
            )
            return (await self._session.execute(statement)).scalar_one_or_none()
        except SQLAlchemyError as error:
            logger.exception("Could not get refresh session by token hash.")
            raise AppError(AppErrorCode.DATABASE_ERROR) from error

    async def revoke_refresh_session(
        self, refresh_session: RefreshSession, revoked_at: datetime
    ) -> None:
        """
        Mark the refresh session as revoked at the given time.
        """
        try:
            refresh_session.revoked_at = revoked_at
            await self._session.flush()
        except SQLAlchemyError as error:
            logger.exception(
                "Could not revoke refresh_session_id=%s.", refresh_session.id
            )
            raise AppError(AppErrorCode.DATABASE_ERROR) from error

    async def revoke_refresh_session_family(
        self, family_id: uuid.UUID, revoked_at: datetime
    ) -> None:
        """
        Revoke every session of the family that is not revoked yet.
        """
        try:
            statement = (
                update(RefreshSession)
                .where(
                    RefreshSession.family_id == family_id,
                    RefreshSession.revoked_at.is_(None),
                )
                .values(revoked_at=revoked_at)
            )
            await self._session.execute(statement)
        except SQLAlchemyError as error:
            logger.exception("Could not revoke family_id=%s.", family_id)
            raise AppError(AppErrorCode.DATABASE_ERROR) from error
