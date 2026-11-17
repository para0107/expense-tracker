import logging
import uuid
from calendar import monthrange
from datetime import date, timedelta
from itertools import count

from expense_tracker.database.session_factory import SessionFactory
from expense_tracker.exceptions.app_error import AppError
from expense_tracker.exceptions.error_codes import AppErrorCode
from expense_tracker.models.pagination import PageResponseModel
from expense_tracker.models.recurring_transaction import (
    CreateRecurringTransactionRequestModel,
    RecurrenceCadence,
    RecurringTransactionResponseModel,
)
from expense_tracker.repositories.account_repository import AccountRepository
from expense_tracker.repositories.category_repository import CategoryRepository
from expense_tracker.repositories.recurring_transaction_repository import (
    RecurringTransactionRepository,
)
from expense_tracker.schemas import RecurringTransaction

logger = logging.getLogger(__name__)

DAYS_PER_WEEK = 7
MONTHS_PER_YEAR = 12


class RecurringTransactionService:
    def __init__(self, session_factory: SessionFactory) -> None:
        self._session_factory = session_factory

    async def create_recurring_transaction(
        self, user_id: uuid.UUID, request: CreateRecurringTransactionRequestModel
    ) -> RecurringTransactionResponseModel:
        """
        Create a recurring rule on one of the user's accounts.

        :param user_id: Owner of the rule.
        :param request: Account, category, amount, description, cadence and start date.
        :return: The created rule.
        :raises AppError: NOT_FOUND when the account or category is missing or not the user's.
        """
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
            recurring_transaction = RecurringTransaction(
                id=uuid.uuid7(),
                account_id=request.account_id,
                category_id=request.category_id,
                amount_minor=request.amount_minor,
                description=request.description,
                cadence=request.cadence,
                start_date=request.start_date,
            )
            await RecurringTransactionRepository(session).create_recurring_transaction(
                recurring_transaction
            )
        return RecurringTransactionResponseModel.model_validate(recurring_transaction)

    async def list_recurring_transactions(
        self, user_id: uuid.UUID, page: int, page_size: int
    ) -> PageResponseModel[RecurringTransactionResponseModel]:
        """
        Return one page of the user's recurring rules.

        :param user_id: Owner of the rules.
        :param page: Page number, starting at the minimum page.
        :param page_size: Number of rules per page.
        :return: The page of rules.
        """
        async with self._session_factory.get_session() as session:
            repository = RecurringTransactionRepository(session)
            recurring_transactions = await repository.list_recurring_transactions(
                user_id, offset=(page - 1) * page_size, limit=page_size
            )
            total_count = await repository.count_recurring_transactions(user_id)
        return PageResponseModel.create(
            [
                RecurringTransactionResponseModel.model_validate(recurring_transaction)
                for recurring_transaction in recurring_transactions
            ],
            page,
            page_size,
            total_count,
        )

    async def delete_recurring_transaction(
        self, user_id: uuid.UUID, recurring_transaction_id: uuid.UUID
    ) -> None:
        """
        Delete the user's recurring rule.

        :param user_id: Owner of the rule.
        :param recurring_transaction_id: Id of the rule.
        :raises AppError: NOT_FOUND when the rule is missing or not the user's.
        """
        async with self._session_factory.get_session() as session:
            is_deleted = await RecurringTransactionRepository(
                session
            ).delete_recurring_transaction(user_id, recurring_transaction_id)
        if not is_deleted:
            raise AppError(AppErrorCode.NOT_FOUND)

    async def create_due_transactions(self, today: date) -> int:
        """
        Book every occurrence of every rule from its start date up to today.

        Occurrences already booked are skipped, so running it again inserts nothing.

        :param today: Last day to book occurrences for.
        :return: How many transactions were inserted.
        """
        async with self._session_factory.get_session() as session:
            repository = RecurringTransactionRepository(session)
            recurring_transactions = await repository.list_all_recurring_transactions()
            rows = [
                {
                    "id": uuid.uuid7(),
                    "account_id": recurring_transaction.account_id,
                    "category_id": recurring_transaction.category_id,
                    "amount_minor": recurring_transaction.amount_minor,
                    "booked_on": booked_on,
                    "description": recurring_transaction.description,
                    "recurring_transaction_id": recurring_transaction.id,
                }
                for recurring_transaction in recurring_transactions
                for booked_on in _build_occurrence_dates(recurring_transaction, today)
            ]
            if not rows:
                return 0
            return await repository.create_recurring_occurrences(rows)


def _build_occurrence_dates(
    recurring_transaction: RecurringTransaction, today: date
) -> list[date]:
    start_date = recurring_transaction.start_date
    occurrence_dates = []
    for occurrence_index in count():
        if recurring_transaction.cadence == RecurrenceCadence.WEEKLY:
            occurrence_date = start_date + timedelta(
                days=DAYS_PER_WEEK * occurrence_index
            )
        else:
            month_index = start_date.month - 1 + occurrence_index
            year = start_date.year + month_index // MONTHS_PER_YEAR
            month = month_index % MONTHS_PER_YEAR + 1
            last_day_of_month = monthrange(year, month)[1]
            occurrence_date = date(year, month, min(start_date.day, last_day_of_month))
        if occurrence_date > today:
            return occurrence_dates
        occurrence_dates.append(occurrence_date)
