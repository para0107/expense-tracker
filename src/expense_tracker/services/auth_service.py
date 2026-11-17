import logging
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from expense_tracker.configuration.config import AuthSettings
from expense_tracker.database.session_factory import SessionFactory
from expense_tracker.exceptions.app_error import AppError
from expense_tracker.exceptions.error_codes import AppErrorCode
from expense_tracker.models.auth import (
    AuthenticatedUserModel,
    IssuedTokensModel,
    LoginRequestModel,
    RegisterRequestModel,
    UserResponseModel,
)
from expense_tracker.repositories.refresh_session_repository import (
    RefreshSessionRepository,
)
from expense_tracker.repositories.user_repository import UserRepository
from expense_tracker.schemas import RefreshSession, User
from expense_tracker.security.password_hashing import hash_password, verify_password
from expense_tracker.security.token_service import TokenService

logger = logging.getLogger(__name__)


class AuthService:
    def __init__(
        self,
        session_factory: SessionFactory,
        token_service: TokenService,
        auth_settings: AuthSettings,
        dummy_password_hash: str,
    ) -> None:
        self._session_factory = session_factory
        self._token_service = token_service
        self._auth_settings = auth_settings
        self._dummy_password_hash = dummy_password_hash

    async def register_user(self, request: RegisterRequestModel) -> UserResponseModel:
        """
        Create a user with a lowercase email and a hashed password.

        :param request: Email and password of the new user.
        :return: The created user.
        :raises AppError: EMAIL_ALREADY_REGISTERED when the email is taken.
        """
        user = User(
            id=uuid.uuid7(),
            email=request.email.lower(),
            password_hash=await hash_password(request.password),
        )
        try:
            async with self._session_factory.get_session() as session:
                await UserRepository(session).create_user(user)
        except IntegrityError as error:
            logger.warning("Registration rejected, email already registered.")
            raise AppError(AppErrorCode.EMAIL_ALREADY_REGISTERED) from error
        return UserResponseModel(id=user.id, email=user.email)

    async def login_user(
        self, request: LoginRequestModel
    ) -> tuple[UserResponseModel, IssuedTokensModel]:
        """
        Check the credentials and start a new token family.

        An unknown email is verified against a dummy hash, so it costs the same
        as a wrong password.

        :param request: Email and password.
        :return: The user and the tokens to set as cookies.
        :raises AppError: INVALID_CREDENTIALS when the email or password is wrong.
        """
        async with self._session_factory.get_session() as session:
            user = await UserRepository(session).get_user_by_email(
                request.email.lower()
            )
        password_hash = user.password_hash if user else self._dummy_password_hash
        is_password_valid = await verify_password(password_hash, request.password)
        if user is None or not is_password_valid:
            logger.warning("Login rejected, wrong credentials.")
            raise AppError(AppErrorCode.INVALID_CREDENTIALS)
        async with self._session_factory.get_session() as session:
            tokens = await self._create_tokens(session, user.id, uuid.uuid7())
        return UserResponseModel(id=user.id, email=user.email), tokens

    async def refresh_tokens(self, refresh_token: str) -> IssuedTokensModel:
        """
        Rotate the refresh token inside its family.

        A token that was already revoked revokes the whole family.

        :param refresh_token: The refresh token from the cookie.
        :return: The new tokens to set as cookies.
        :raises AppError: INVALID_REFRESH_TOKEN when the token is unknown, expired
            or was already used.
        """
        token_hash = self._token_service.hash_refresh_token(refresh_token)
        now = datetime.now(UTC)
        async with self._session_factory.get_session() as session:
            repository = RefreshSessionRepository(session)
            refresh_session = (
                await repository.get_refresh_session_by_token_hash_for_update(
                    token_hash
                )
            )
            if refresh_session is None or refresh_session.expires_at <= now:
                logger.warning("Refresh rejected, token unknown or expired.")
                raise AppError(AppErrorCode.INVALID_REFRESH_TOKEN)
            is_reuse = refresh_session.revoked_at is not None
            if is_reuse:
                await repository.revoke_refresh_session_family(
                    refresh_session.family_id, now
                )
            else:
                await repository.revoke_refresh_session(refresh_session, now)
                tokens = await self._create_tokens(
                    session, refresh_session.user_id, refresh_session.family_id
                )
        if is_reuse:
            logger.warning(
                "Revoked token reused, family_id=%s revoked.", refresh_session.family_id
            )
            raise AppError(AppErrorCode.INVALID_REFRESH_TOKEN)
        return tokens

    async def revoke_refresh_session_family(self, family_id: uuid.UUID) -> None:
        """
        Revoke every refresh session of the family, for logout.
        """
        async with self._session_factory.get_session() as session:
            await RefreshSessionRepository(session).revoke_refresh_session_family(
                family_id, datetime.now(UTC)
            )

    async def get_authenticated_user(
        self, access_token: str
    ) -> AuthenticatedUserModel | None:
        """
        Return the user an access token belongs to, or None when the token is
        invalid or the user no longer exists.
        """
        claims = self._token_service.read_access_token_claims(access_token)
        if claims is None:
            return None
        async with self._session_factory.get_session() as session:
            user = await UserRepository(session).get_user_by_id(claims.user_id)
        if user is None:
            return None
        return AuthenticatedUserModel(
            id=user.id, email=user.email, family_id=claims.family_id
        )

    async def _create_tokens(
        self, session: AsyncSession, user_id: uuid.UUID, family_id: uuid.UUID
    ) -> IssuedTokensModel:
        refresh_token = self._token_service.create_refresh_token()
        await RefreshSessionRepository(session).create_refresh_session(
            RefreshSession(
                id=uuid.uuid7(),
                user_id=user_id,
                family_id=family_id,
                token_hash=self._token_service.hash_refresh_token(refresh_token),
                expires_at=datetime.now(UTC)
                + timedelta(days=self._auth_settings.refresh_token_expire_days),
            )
        )
        return IssuedTokensModel(
            access_token=self._token_service.create_access_token(user_id, family_id),
            refresh_token=refresh_token,
        )
