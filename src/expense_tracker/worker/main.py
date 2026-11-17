import asyncio
import logging
from datetime import date

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from expense_tracker.configuration.config import get_settings
from expense_tracker.configuration.log_config import setup_logging
from expense_tracker.database.database import setup_database_engine
from expense_tracker.database.session_factory import SessionFactory
from expense_tracker.services.recurring_transaction_service import (
    RecurringTransactionService,
)

logger = logging.getLogger(__name__)


async def create_due_transactions_and_log_count(
    recurring_transaction_service: RecurringTransactionService,
) -> None:
    """
    Book today's due recurring transactions and log how many were created.

    :param recurring_transaction_service: Service that inserts the due rows.
    """
    inserted_count = await recurring_transaction_service.create_due_transactions(
        date.today()
    )
    logger.info("Created %s due recurring transactions.", inserted_count)


async def start_recurring_transaction_worker() -> None:
    """Book due transactions now and on every interval, then stop and dispose."""
    settings = get_settings()
    setup_logging(settings.log)
    engine = setup_database_engine(settings.database)
    scheduler = AsyncIOScheduler()
    try:
        recurring_transaction_service = RecurringTransactionService(
            SessionFactory(engine)
        )
        await create_due_transactions_and_log_count(recurring_transaction_service)
        scheduler.add_job(
            create_due_transactions_and_log_count,
            "interval",
            minutes=settings.worker.recurring_interval_minutes,
            args=[recurring_transaction_service],
        )
        scheduler.start()
        await asyncio.Event().wait()
    finally:
        if scheduler.running:
            scheduler.shutdown(wait=False)
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(start_recurring_transaction_worker())
