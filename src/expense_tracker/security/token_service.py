import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta

import jwt

from expense_tracker.configuration.config import AuthSettings
from expense_tracker.models.auth import AccessTokenClaims

ACCESS_TOKEN_TYPE = "access"
REFRESH_TOKEN_BYTES = 32


class TokenService:
    def __init__(self, auth_settings: AuthSettings) -> None:
        self._auth_settings = auth_settings

    def create_access_token(self, user_id: uuid.UUID, family_id: uuid.UUID) -> str:
        """
        Sign an access token for the user, tied to the login family.
        """
        expires_at = datetime.now(UTC) + timedelta(
            minutes=self._auth_settings.access_token_expire_minutes
        )
        claims = {
            "sub": str(user_id),
            "type": ACCESS_TOKEN_TYPE,
            "family_id": str(family_id),
            "exp": expires_at,
        }
        return jwt.encode(
            claims,
            self._auth_settings.jwt_secret_key.get_secret_value(),
            algorithm=self._auth_settings.jwt_algorithm,
        )

    def read_access_token_claims(self, token: str) -> AccessTokenClaims | None:
        """
        Return the claims of a valid access token, or None when the token is
        invalid, expired or not an access token.
        """
        try:
            claims = jwt.decode(
                token,
                self._auth_settings.jwt_secret_key.get_secret_value(),
                algorithms=[self._auth_settings.jwt_algorithm],
                options={"require": ["exp", "sub"]},
            )
            if claims.get("type") != ACCESS_TOKEN_TYPE:
                return None
            return AccessTokenClaims(
                user_id=uuid.UUID(claims["sub"]),
                family_id=uuid.UUID(claims["family_id"]),
            )
        except jwt.PyJWTError, KeyError, ValueError:
            return None

    def create_refresh_token(self) -> str:
        """
        Return a new random refresh token.
        """
        return secrets.token_urlsafe(REFRESH_TOKEN_BYTES)

    def hash_refresh_token(self, token: str) -> str:
        """
        Return the SHA-256 hex digest under which the token is stored.
        """
        return hashlib.sha256(token.encode()).hexdigest()
