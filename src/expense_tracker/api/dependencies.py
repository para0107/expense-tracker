from typing import Annotated

from fastapi import Depends, Request

from expense_tracker.configuration.config import Settings
from expense_tracker.database.session_factory import SessionFactory
from expense_tracker.exceptions.app_error import AppError
from expense_tracker.exceptions.error_codes import AppErrorCode
from expense_tracker.models.auth import AuthenticatedUserModel
from expense_tracker.services.account_service import AccountService
from expense_tracker.services.auth_service import AuthService
from expense_tracker.services.budget_service import BudgetService
from expense_tracker.services.category_service import CategoryService
from expense_tracker.services.csv_import_service import CSVImportService
from expense_tracker.services.health_service import HealthService
from expense_tracker.services.recurring_transaction_service import (
    RecurringTransactionService,
)
from expense_tracker.services.report_service import ReportService
from expense_tracker.services.tag_service import TagService
from expense_tracker.services.transaction_service import TransactionService


def get_settings_from_state(request: Request) -> Settings:
    return request.app.state.settings


def get_session_factory(request: Request) -> SessionFactory:
    return request.app.state.session_factory


def get_auth_service(request: Request) -> AuthService:
    return request.app.state.auth_service


def get_current_user(request: Request) -> AuthenticatedUserModel:
    current_user = request.state.current_user
    if current_user is None:
        raise AppError(AppErrorCode.UNAUTHORIZED)
    return current_user


CurrentUser = Annotated[AuthenticatedUserModel, Depends(get_current_user)]


def get_account_service(
    session_factory: Annotated[SessionFactory, Depends(get_session_factory)],
) -> AccountService:
    return AccountService(session_factory)


def get_category_service(
    session_factory: Annotated[SessionFactory, Depends(get_session_factory)],
) -> CategoryService:
    return CategoryService(session_factory)


def get_tag_service(
    session_factory: Annotated[SessionFactory, Depends(get_session_factory)],
) -> TagService:
    return TagService(session_factory)


def get_transaction_service(
    session_factory: Annotated[SessionFactory, Depends(get_session_factory)],
) -> TransactionService:
    return TransactionService(session_factory)


def get_budget_service(
    session_factory: Annotated[SessionFactory, Depends(get_session_factory)],
) -> BudgetService:
    return BudgetService(session_factory)


def get_recurring_transaction_service(
    session_factory: Annotated[SessionFactory, Depends(get_session_factory)],
) -> RecurringTransactionService:
    return RecurringTransactionService(session_factory)


def get_report_service(
    session_factory: Annotated[SessionFactory, Depends(get_session_factory)],
) -> ReportService:
    return ReportService(session_factory)


def get_csv_import_service(
    session_factory: Annotated[SessionFactory, Depends(get_session_factory)],
    settings: Annotated[Settings, Depends(get_settings_from_state)],
) -> CSVImportService:
    return CSVImportService(session_factory, settings.csv_import)


def get_health_service(
    session_factory: Annotated[SessionFactory, Depends(get_session_factory)],
) -> HealthService:
    return HealthService(session_factory)
