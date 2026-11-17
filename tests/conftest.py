import os

os.environ["LOG__LEVEL"] = "INFO"
os.environ["AUTH__JWT_SECRET_KEY"] = "test-secret-key-" + "x" * 48
os.environ["AUTH__JWT_ALGORITHM"] = "HS256"
os.environ["AUTH__ACCESS_TOKEN_EXPIRE_MINUTES"] = "15"
os.environ["AUTH__REFRESH_TOKEN_EXPIRE_DAYS"] = "7"
os.environ["CSV_IMPORT__MAX_FILE_SIZE_BYTES"] = "1048576"
os.environ["WORKER__RECURRING_INTERVAL_MINUTES"] = "60"

from collections.abc import AsyncIterator

import pytest
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from alembic import command
from expense_tracker.api.app import app
from expense_tracker.api.paths import API_PREFIX
from expense_tracker.database.session_factory import SessionFactory
from expense_tracker.schemas import Base

TEST_BASE_URL = "https://testserver"
TEST_PASSWORD = "correct horse battery"


@pytest.fixture(scope="session")
def migrated_database() -> None:
    command.upgrade(Config("alembic.ini"), "head")


@pytest.fixture(autouse=True)
async def truncate_tables(request: pytest.FixtureRequest) -> AsyncIterator[None]:
    yield
    if "app_lifespan" not in request.fixturenames:
        return
    table_names = ", ".join(table.name for table in Base.metadata.sorted_tables)
    if table_names:
        async with app.state.session_factory.get_session() as session:
            await session.execute(text(f"TRUNCATE {table_names} CASCADE"))


@pytest.fixture(scope="session")
async def app_lifespan(migrated_database: None) -> AsyncIterator[None]:
    async with app.router.lifespan_context(app):
        yield


@pytest.fixture
async def client(app_lifespan: None) -> AsyncIterator[AsyncClient]:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url=TEST_BASE_URL
    ) as test_client:
        yield test_client


async def register_and_login(test_client: AsyncClient, email: str) -> None:
    credentials = {"email": email, "password": TEST_PASSWORD}
    await test_client.post(f"{API_PREFIX}/auth/register", json=credentials)
    await test_client.post(f"{API_PREFIX}/auth/login", json=credentials)


@pytest.fixture
async def logged_in_client(app_lifespan: None) -> AsyncIterator[AsyncClient]:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url=TEST_BASE_URL
    ) as test_client:
        await register_and_login(test_client, "user-a@example.com")
        yield test_client


@pytest.fixture
async def other_logged_in_client(app_lifespan: None) -> AsyncIterator[AsyncClient]:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url=TEST_BASE_URL
    ) as test_client:
        await register_and_login(test_client, "user-b@example.com")
        yield test_client


@pytest.fixture
def session_factory(app_lifespan: None) -> SessionFactory:
    return app.state.session_factory
