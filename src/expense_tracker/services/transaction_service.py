import logging
import uuid
from datetime import date

from expense_tracker.database.session_factory import SessionFactory
from expense_tracker.exceptions.app_error import AppError
from expense_tracker.exceptions.error_codes import AppErrorCode
from expense_tracker.models.pagination import PageResponseModel
from expense_tracker.models.transaction import (
    CreateTransactionRequestModel,
    TransactionResponseModel,
)
from expense_tracker.repositories.account_repository import AccountRepository
from expense_tracker.repositories.category_repository import CategoryRepository
from expense_tracker.repositories.tag_repository import TagRepository
from expense_tracker.repositories.transaction_repository import TransactionRepository
from expense_tracker.schemas import Transaction

logger = logging.getLogger(__name__)


class TransactionService:
    def __init__(self, session_factory: SessionFactory) -> None:
        self._session_factory = session_factory

    async def create_transaction(
        self, user_id: uuid.UUID, request: CreateTransactionRequestModel
    ) -> TransactionResponseModel:
        """
        Create a transaction on one of the user's accounts.

        :param user_id: Owner of the transaction.
        :param request: Account, category, tags, amount, date and description.
        :return: The created transaction.
        :raises AppError: NOT_FOUND when the account, category or any tag is missing or not the user's.
        """
        tag_ids = set(request.tag_ids)
        async with self._session_factory.get_session() as session:
            account = await AccountRepository(session).get_account_by_id(
                user_id, request.account_id
            )
            if account is None:
                logger.warning(
                    "Account_id=%s not found for user_id=%s.",
                    request.account_id,
                    user_id,
                )
                raise AppError(AppErrorCode.NOT_FOUND)
            if request.category_id is not None:
                category = await CategoryRepository(session).get_category_by_id(
                    user_id, request.category_id
                )
                if category is None:
                    logger.warning(
                        "Category_id=%s not found for user_id=%s.",
                        request.category_id,
                        user_id,
                    )
                    raise AppError(AppErrorCode.NOT_FOUND)
            tags = await TagRepository(session).list_tags_by_ids(user_id, tag_ids)
            if len(tags) != len(tag_ids):
                logger.warning("Some tags not found for user_id=%s.", user_id)
                raise AppError(AppErrorCode.NOT_FOUND)
            transaction = Transaction(
                id=uuid.uuid7(),
                account_id=request.account_id,
                category_id=request.category_id,
                amount_minor=request.amount_minor,
                booked_on=request.booked_on,
                description=request.description,
                tags=tags,
            )
            await TransactionRepository(session).create_transaction(transaction)
        return TransactionResponseModel.model_validate(transaction)

    async def list_transactions(
        self,
        user_id: uuid.UUID,
        date_from: date | None,
        date_to: date | None,
        account_id: uuid.UUID | None,
        category_id: uuid.UUID | None,
        tag_id: uuid.UUID | None,
        page: int,
        page_size: int,
    ) -> PageResponseModel[TransactionResponseModel]:
        """
        Return one page of the user's transactions that match the filters.

        :param user_id: Owner of the transactions.
        :param date_from: First day to include, if any.
        :param date_to: Last day to include, if any.
        :param account_id: Only this account, if any.
        :param category_id: Only this category, if any.
        :param tag_id: Only transactions with this tag, if any.
        :param page: Page number, starting at the minimum page.
        :param page_size: Number of transactions per page.
        :return: The page of transactions, newest first.
        """
        async with self._session_factory.get_session() as session:
            repository = TransactionRepository(session)
            transactions = await repository.list_transactions(
                user_id,
                date_from,
                date_to,
                account_id,
                category_id,
                tag_id,
                offset=(page - 1) * page_size,
                limit=page_size,
            )
            total_count = await repository.count_transactions(
                user_id, date_from, date_to, account_id, category_id, tag_id
            )
        return PageResponseModel.create(
            [
                TransactionResponseModel.model_validate(transaction)
                for transaction in transactions
            ],
            page,
            page_size,
            total_count,
        )

    async def get_transaction(
        self, user_id: uuid.UUID, transaction_id: uuid.UUID
    ) -> TransactionResponseModel:
        """
        Return the user's transaction.

        :param user_id: Owner of the transaction.
        :param transaction_id: Id of the transaction.
        :return: The transaction.
        :raises AppError: NOT_FOUND when the transaction is missing or not the user's.
        """
        async with self._session_factory.get_session() as session:
            transaction = await TransactionRepository(session).get_transaction_by_id(
                user_id, transaction_id
            )
        if transaction is None:
            raise AppError(AppErrorCode.NOT_FOUND)
        return TransactionResponseModel.model_validate(transaction)

    async def delete_transaction(
        self, user_id: uuid.UUID, transaction_id: uuid.UUID
    ) -> None:
        """
        Delete the user's transaction.

        :param user_id: Owner of the transaction.
        :param transaction_id: Id of the transaction.
        :raises AppError: NOT_FOUND when the transaction is missing or not the user's.
        """
        async with self._session_factory.get_session() as session:
            is_deleted = await TransactionRepository(session).delete_transaction(
                user_id, transaction_id
            )
        if not is_deleted:
            raise AppError(AppErrorCode.NOT_FOUND)
