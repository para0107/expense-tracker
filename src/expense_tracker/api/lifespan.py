from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from expense_tracker.configuration.config import get_settings
from expense_tracker.configuration.log_config import setup_logging
from expense_tracker.database.database import setup_database_engine
from expense_tracker.database.session_factory import SessionFactory
from expense_tracker.security.password_hashing import hash_password
from expense_tracker.security.token_service import TokenService
from expense_tracker.services.auth_service import AuthService
from expense_tracker.services.health_service import HealthService

DUMMY_PASSWORD = "password-nobody-has"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    setup_logging(settings.log)
    engine = setup_database_engine(settings.database)
    try:
        session_factory = SessionFactory(engine)
        await HealthService(session_factory).check_database()
        app.state.settings = settings
        app.state.session_factory = session_factory
        app.state.auth_service = AuthService(
            session_factory,
            TokenService(settings.auth),
            settings.auth,
            await hash_password(DUMMY_PASSWORD),
        )
        yield
    finally:
        await engine.dispose()
