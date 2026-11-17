from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Response

from expense_tracker.api.dependencies import (
    CurrentUser,
    get_auth_service,
    get_settings_from_state,
)
from expense_tracker.api.paths import (
    ACCESS_TOKEN_COOKIE_NAME,
    ACCESS_TOKEN_COOKIE_PATH,
    REFRESH_TOKEN_COOKIE_NAME,
    REFRESH_TOKEN_COOKIE_PATH,
)
from expense_tracker.configuration.config import AuthSettings, Settings
from expense_tracker.exceptions.app_error import AppError
from expense_tracker.exceptions.error_codes import AppErrorCode
from expense_tracker.exceptions.status_codes import AppStatusCode
from expense_tracker.models.auth import (
    IssuedTokensModel,
    LoginRequestModel,
    RegisterRequestModel,
    UserResponseModel,
)
from expense_tracker.models.error import ErrorResponseModel
from expense_tracker.services.auth_service import AuthService

SECONDS_PER_MINUTE = 60
SECONDS_PER_DAY = 24 * 60 * SECONDS_PER_MINUTE
COOKIE_SAMESITE = "strict"

router = APIRouter(prefix="/auth", tags=["auth"])

AuthServiceDependency = Annotated[AuthService, Depends(get_auth_service)]
SettingsDependency = Annotated[Settings, Depends(get_settings_from_state)]


def _set_token_cookies(
    response: Response, tokens: IssuedTokensModel, auth_settings: AuthSettings
) -> None:
    response.set_cookie(
        ACCESS_TOKEN_COOKIE_NAME,
        tokens.access_token,
        max_age=auth_settings.access_token_expire_minutes * SECONDS_PER_MINUTE,
        path=ACCESS_TOKEN_COOKIE_PATH,
        httponly=True,
        secure=True,
        samesite=COOKIE_SAMESITE,
    )
    response.set_cookie(
        REFRESH_TOKEN_COOKIE_NAME,
        tokens.refresh_token,
        max_age=auth_settings.refresh_token_expire_days * SECONDS_PER_DAY,
        path=REFRESH_TOKEN_COOKIE_PATH,
        httponly=True,
        secure=True,
        samesite=COOKIE_SAMESITE,
    )


def _delete_token_cookies(response: Response) -> None:
    for name, path in (
        (ACCESS_TOKEN_COOKIE_NAME, ACCESS_TOKEN_COOKIE_PATH),
        (REFRESH_TOKEN_COOKIE_NAME, REFRESH_TOKEN_COOKIE_PATH),
    ):
        response.delete_cookie(
            name, path=path, httponly=True, secure=True, samesite=COOKIE_SAMESITE
        )


@router.post(
    "/register",
    response_model=UserResponseModel,
    status_code=AppStatusCode.CREATED,
    responses=ErrorResponseModel.error_response(
        AppErrorCode.EMAIL_ALREADY_REGISTERED, "The email is already registered."
    )
    | ErrorResponseModel.error_response(
        AppErrorCode.VALIDATION_ERROR, "The email or password is not valid."
    ),
)
async def register_user(
    request: RegisterRequestModel, auth_service: AuthServiceDependency
) -> UserResponseModel:
    """
    Create an account. Registration is public, a named deviation for a personal app.
    """
    return await auth_service.register_user(request)


@router.post(
    "/login",
    response_model=UserResponseModel,
    status_code=AppStatusCode.OK,
    responses=ErrorResponseModel.error_response(
        AppErrorCode.INVALID_CREDENTIALS, "The email or password is wrong."
    ),
)
async def login_user(
    request: LoginRequestModel,
    response: Response,
    auth_service: AuthServiceDependency,
    settings: SettingsDependency,
) -> UserResponseModel:
    """
    Log in and set the access and refresh cookies.
    """
    user, tokens = await auth_service.login_user(request)
    _set_token_cookies(response, tokens, settings.auth)
    return user


@router.post(
    "/refresh",
    response_model=None,
    status_code=AppStatusCode.NO_CONTENT,
    responses=ErrorResponseModel.error_response(
        AppErrorCode.INVALID_REFRESH_TOKEN, "The refresh token is missing or invalid."
    ),
)
async def refresh_tokens(
    response: Response,
    auth_service: AuthServiceDependency,
    settings: SettingsDependency,
    refresh_token: Annotated[
        str | None, Cookie(alias=REFRESH_TOKEN_COOKIE_NAME)
    ] = None,
) -> None:
    """
    Rotate the refresh token and set new cookies.
    """
    if refresh_token is None:
        raise AppError(AppErrorCode.INVALID_REFRESH_TOKEN)
    tokens = await auth_service.refresh_tokens(refresh_token)
    _set_token_cookies(response, tokens, settings.auth)


@router.post(
    "/logout",
    response_model=None,
    status_code=AppStatusCode.NO_CONTENT,
    responses=ErrorResponseModel.error_response(
        AppErrorCode.UNAUTHORIZED, "The caller is not logged in."
    ),
)
async def logout_user(
    response: Response, current_user: CurrentUser, auth_service: AuthServiceDependency
) -> None:
    """
    Revoke the login's refresh tokens and delete both cookies.
    """
    await auth_service.revoke_refresh_session_family(current_user.family_id)
    _delete_token_cookies(response)


@router.get(
    "/me",
    response_model=UserResponseModel,
    status_code=AppStatusCode.OK,
    responses=ErrorResponseModel.error_response(
        AppErrorCode.UNAUTHORIZED, "The caller is not logged in."
    ),
)
async def get_me(current_user: CurrentUser) -> UserResponseModel:
    """
    Return the logged-in user.
    """
    return UserResponseModel(id=current_user.id, email=current_user.email)
