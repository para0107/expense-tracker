from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import update

from expense_tracker.configuration.config import get_settings
from expense_tracker.database.session_factory import SessionFactory
from expense_tracker.exceptions.app_error import AppError
from expense_tracker.exceptions.error_codes import AppErrorCode
from expense_tracker.models.auth import LoginRequestModel, RegisterRequestModel
from expense_tracker.schemas import RefreshSession
from expense_tracker.security.password_hashing import hash_password
from expense_tracker.security.token_service import TokenService
from expense_tracker.services.auth_service import AuthService

EMAIL = "Person@Example.com"
PASSWORD = "correct horse battery"


@pytest.fixture
async def auth_service(session_factory: SessionFactory) -> AuthService:
    auth_settings = get_settings().auth
    return AuthService(
        session_factory,
        TokenService(auth_settings),
        auth_settings,
        await hash_password("dummy-password"),
    )


async def test_register_then_duplicate_conflicts(auth_service: AuthService) -> None:
    user = await auth_service.register_user(
        RegisterRequestModel(email=EMAIL, password=PASSWORD)
    )

    assert user.email == EMAIL.lower()
    with pytest.raises(AppError) as raised:
        await auth_service.register_user(
            RegisterRequestModel(email=EMAIL.upper(), password=PASSWORD)
        )
    assert raised.value.error is AppErrorCode.EMAIL_ALREADY_REGISTERED


async def test_login_ok_and_same_error_for_wrong_password_and_unknown_email(
    auth_service: AuthService,
) -> None:
    await auth_service.register_user(
        RegisterRequestModel(email=EMAIL, password=PASSWORD)
    )

    user, tokens = await auth_service.login_user(
        LoginRequestModel(email=EMAIL, password=PASSWORD)
    )
    assert tokens.access_token and tokens.refresh_token
    authenticated = await auth_service.get_authenticated_user(tokens.access_token)
    assert authenticated is not None and authenticated.id == user.id

    for email, password in ((EMAIL, "wrong"), ("nobody@example.com", PASSWORD)):
        with pytest.raises(AppError) as raised:
            await auth_service.login_user(
                LoginRequestModel(email=email, password=password)
            )
        assert raised.value.error is AppErrorCode.INVALID_CREDENTIALS


async def login(auth_service: AuthService):
    await auth_service.register_user(
        RegisterRequestModel(email=EMAIL, password=PASSWORD)
    )
    _, tokens = await auth_service.login_user(
        LoginRequestModel(email=EMAIL, password=PASSWORD)
    )
    return tokens


async def test_refresh_rotates(auth_service: AuthService) -> None:
    tokens = await login(auth_service)

    rotated = await auth_service.refresh_tokens(tokens.refresh_token)

    assert rotated.refresh_token != tokens.refresh_token
    await auth_service.refresh_tokens(rotated.refresh_token)


async def test_reused_token_revokes_family(auth_service: AuthService) -> None:
    tokens = await login(auth_service)
    rotated = await auth_service.refresh_tokens(tokens.refresh_token)

    for token in (tokens.refresh_token, rotated.refresh_token):
        with pytest.raises(AppError) as raised:
            await auth_service.refresh_tokens(token)
        assert raised.value.error is AppErrorCode.INVALID_REFRESH_TOKEN


async def test_expired_token_fails(
    auth_service: AuthService, session_factory: SessionFactory
) -> None:
    tokens = await login(auth_service)
    async with session_factory.get_session() as session:
        await session.execute(
            update(RefreshSession).values(
                expires_at=datetime.now(UTC) - timedelta(minutes=1)
            )
        )

    with pytest.raises(AppError) as raised:
        await auth_service.refresh_tokens(tokens.refresh_token)
    assert raised.value.error is AppErrorCode.INVALID_REFRESH_TOKEN
