import logging

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from expense_tracker.database.session_factory import SessionFactory
from expense_tracker.exceptions.app_error import AppError
from expense_tracker.exceptions.error_codes import AppErrorCode

logger = logging.getLogger(__name__)


class HealthService:
    def __init__(self, session_factory: SessionFactory) -> None:
        self._session_factory = session_factory

    async def check_database(self) -> None:
        """
        Run a trivial query to prove the database answers.

        :raises AppError: DATABASE_UNAVAILABLE when the query fails.
        """
        try:
            async with self._session_factory.get_session() as session:
                await session.execute(text("SELECT 1"))
        except SQLAlchemyError as error:
            logger.exception("Database health check failed.")
            raise AppError(AppErrorCode.DATABASE_UNAVAILABLE) from error
