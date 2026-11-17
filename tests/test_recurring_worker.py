from datetime import date

from httpx import AsyncClient
from sqlalchemy import select

from expense_tracker.api.paths import API_PREFIX
from expense_tracker.database.session_factory import SessionFactory
from expense_tracker.schemas import Transaction
from expense_tracker.services.recurring_transaction_service import (
    RecurringTransactionService,
)

RECURRING_URL = f"{API_PREFIX}/recurring-transactions"
ACCOUNTS_URL = f"{API_PREFIX}/accounts"
TODAY = date(2026, 4, 30)
WEEKLY_DATES = [
    date(2026, 4, 6),
    date(2026, 4, 13),
    date(2026, 4, 20),
    date(2026, 4, 27),
]
MONTHLY_DATES = [
    date(2026, 1, 31),
    date(2026, 2, 28),
    date(2026, 3, 31),
    date(2026, 4, 30),
]


async def create_rule(
    client: AsyncClient, account_id: str, cadence: str, start_date: str
) -> None:
    response = await client.post(
        RECURRING_URL,
        json={
            "accountId": account_id,
            "amountMinor": -1000,
            "description": cadence,
            "cadence": cadence,
            "startDate": start_date,
        },
    )
    assert response.status_code == 201


async def list_booked_dates(
    session_factory: SessionFactory, description: str
) -> list[date]:
    async with session_factory.get_session() as session:
        statement = (
            select(Transaction.booked_on)
            .where(Transaction.description == description)
            .order_by(Transaction.booked_on)
        )
        return list((await session.execute(statement)).scalars())


async def test_due_transactions_are_created_once(
    logged_in_client: AsyncClient, session_factory: SessionFactory
) -> None:
    account = await logged_in_client.post(
        ACCOUNTS_URL, json={"name": "Checking", "currency": "EUR"}
    )
    account_id = account.json()["id"]
    await create_rule(logged_in_client, account_id, "WEEKLY", "2026-04-06")
    await create_rule(logged_in_client, account_id, "MONTHLY", "2026-01-31")
    service = RecurringTransactionService(session_factory)

    assert await service.create_due_transactions(TODAY) == 8
    assert await list_booked_dates(session_factory, "WEEKLY") == WEEKLY_DATES
    assert await list_booked_dates(session_factory, "MONTHLY") == MONTHLY_DATES

    assert await service.create_due_transactions(TODAY) == 0
    assert len(await list_booked_dates(session_factory, "WEEKLY")) == 4
    assert len(await list_booked_dates(session_factory, "MONTHLY")) == 4
