import logging
import uuid

from sqlalchemy.exc import IntegrityError

from expense_tracker.database.session_factory import SessionFactory
from expense_tracker.exceptions.app_error import AppError
from expense_tracker.exceptions.error_codes import AppErrorCode
from expense_tracker.models.account import (
    AccountResponseModel,
    CreateAccountRequestModel,
)
from expense_tracker.models.pagination import PageResponseModel
from expense_tracker.repositories.account_repository import AccountRepository
from expense_tracker.schemas import Account

logger = logging.getLogger(__name__)


class AccountService:
    def __init__(self, session_factory: SessionFactory) -> None:
        self._session_factory = session_factory

    async def create_account(
        self, user_id: uuid.UUID, request: CreateAccountRequestModel
    ) -> AccountResponseModel:
        """
        Create an account for the user.

        :param user_id: Owner of the new account.
        :param request: Name and currency of the account.
        :return: The created account.
        :raises AppError: CONFLICT when the user already has an account with this name.
        """
        account = Account(
            id=uuid.uuid7(),
            user_id=user_id,
            name=request.name,
            currency=request.currency,
        )
        try:
            async with self._session_factory.get_session() as session:
                await AccountRepository(session).create_account(account)
        except IntegrityError as error:
            logger.warning(
                "Account rejected, name already used by user_id=%s.", user_id
            )
            raise AppError(AppErrorCode.CONFLICT) from error
        return AccountResponseModel.model_validate(account)

    async def list_accounts(
        self, user_id: uuid.UUID, page: int, page_size: int
    ) -> PageResponseModel[AccountResponseModel]:
        """
        Return one page of the user's accounts.

        :param user_id: Owner of the accounts.
        :param page: Page number, starting at the minimum page.
        :param page_size: Number of accounts per page.
        :return: The page of accounts.
        """
        async with self._session_factory.get_session() as session:
            repository = AccountRepository(session)
            accounts = await repository.list_accounts(
                user_id, offset=(page - 1) * page_size, limit=page_size
            )
            total_count = await repository.count_accounts(user_id)
        return PageResponseModel.create(
            [AccountResponseModel.model_validate(account) for account in accounts],
            page,
            page_size,
            total_count,
        )

    async def get_account(
        self, user_id: uuid.UUID, account_id: uuid.UUID
    ) -> AccountResponseModel:
        """
        Return the user's account.

        :param user_id: Owner of the account.
        :param account_id: Id of the account.
        :return: The account.
        :raises AppError: NOT_FOUND when the account is missing or not the user's.
        """
        async with self._session_factory.get_session() as session:
            account = await AccountRepository(session).get_account_by_id(
                user_id, account_id
            )
        if account is None:
            raise AppError(AppErrorCode.NOT_FOUND)
        return AccountResponseModel.model_validate(account)

    async def delete_account(self, user_id: uuid.UUID, account_id: uuid.UUID) -> None:
        """
        Delete the user's account.

        :param user_id: Owner of the account.
        :param account_id: Id of the account.
        :raises AppError: NOT_FOUND when the account is missing or not the user's.
        :raises AppError: CONFLICT when other rows still reference the account.
        """
        try:
            async with self._session_factory.get_session() as session:
                is_deleted = await AccountRepository(session).delete_account(
                    user_id, account_id
                )
        except IntegrityError as error:
            logger.warning("Account_id=%s is still referenced.", account_id)
            raise AppError(AppErrorCode.CONFLICT) from error
        if not is_deleted:
            raise AppError(AppErrorCode.NOT_FOUND)
