from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from expense_tracker.configuration.config import DatabaseSettings


def setup_database_engine(database_settings: DatabaseSettings) -> AsyncEngine:
    return create_async_engine(database_settings.url, pool_pre_ping=True)
