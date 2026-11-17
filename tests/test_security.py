import uuid
from datetime import UTC, datetime, timedelta

import jwt
import pytest

from expense_tracker.configuration.config import AuthSettings
from expense_tracker.security.password_hashing import hash_password, verify_password
from expense_tracker.security.token_service import TokenService

SECRET = "unit-test-secret-" + "y" * 48


@pytest.fixture
def auth_settings() -> AuthSettings:
    return AuthSettings(
        jwt_secret_key=SECRET,
        jwt_algorithm="HS256",
        access_token_expire_minutes=15,
        refresh_token_expire_days=7,
    )


@pytest.fixture
def token_service(auth_settings: AuthSettings) -> TokenService:
    return TokenService(auth_settings)


async def test_verify_password_accepts_right_and_rejects_wrong() -> None:
    password_hash = await hash_password("correct horse")

    assert await verify_password(password_hash, "correct horse")
    assert not await verify_password(password_hash, "wrong")
    assert not await verify_password("not-a-hash", "correct horse")


def test_access_token_round_trip(token_service: TokenService) -> None:
    user_id, family_id = uuid.uuid7(), uuid.uuid7()

    claims = token_service.read_access_token_claims(
        token_service.create_access_token(user_id, family_id)
    )

    assert claims is not None
    assert (claims.user_id, claims.family_id) == (user_id, family_id)


def test_invalid_access_tokens_give_none(token_service: TokenService) -> None:
    user_id, family_id = str(uuid.uuid7()), str(uuid.uuid7())
    now = datetime.now(UTC)

    def sign(**overrides: object) -> str:
        claims = {
            "sub": user_id,
            "type": "access",
            "family_id": family_id,
            "exp": now + timedelta(minutes=5),
        } | overrides
        return jwt.encode(claims, SECRET, algorithm="HS256")

    valid = sign()
    assert token_service.read_access_token_claims(valid) is not None
    assert token_service.read_access_token_claims(valid + "x") is None
    assert (
        token_service.read_access_token_claims(sign(exp=now - timedelta(minutes=1)))
        is None
    )
    assert token_service.read_access_token_claims(sign(type="refresh")) is None


def test_refresh_token_hash_is_stable_sha256(token_service: TokenService) -> None:
    token = token_service.create_refresh_token()

    assert token != token_service.create_refresh_token()
    assert token_service.hash_refresh_token(token) == token_service.hash_refresh_token(
        token
    )
    assert len(token_service.hash_refresh_token(token)) == 64
