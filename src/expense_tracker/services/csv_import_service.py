import asyncio
import csv
import hashlib
import io
import logging
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, BinaryIO

from expense_tracker.configuration.config import CSVImportSettings
from expense_tracker.database.session_factory import SessionFactory
from expense_tracker.exceptions.app_error import AppError
from expense_tracker.exceptions.error_codes import AppErrorCode
from expense_tracker.models.csv_import import (
    CSVImportMappingModel,
    CSVImportResponseModel,
)
from expense_tracker.models.transaction import (
    MAX_AMOUNT_MINOR,
    MAX_DESCRIPTION_LENGTH,
    MIN_AMOUNT_MINOR,
)
from expense_tracker.repositories.account_repository import AccountRepository
from expense_tracker.repositories.category_repository import CategoryRepository
from expense_tracker.repositories.transaction_repository import TransactionRepository

logger = logging.getLogger(__name__)

MINOR_UNITS_PER_MAJOR = 100
CSV_ENCODING = "utf-8-sig"


class CSVImportService:
    def __init__(
        self, session_factory: SessionFactory, csv_import_settings: CSVImportSettings
    ) -> None:
        self._session_factory = session_factory
        self._csv_import_settings = csv_import_settings

    async def import_transactions(
        self,
        user_id: uuid.UUID,
        account_id: uuid.UUID,
        stream: BinaryIO,
        mapping: CSVImportMappingModel,
    ) -> CSVImportResponseModel:
        """
        Import the rows of a bank export as transactions, skipping duplicates.

        Rows already imported on the account (same date, amount and description) are skipped, so a row that legitimately repeats within one file is skipped too.

        :param user_id: Owner of the account.
        :param account_id: Account that receives the transactions.
        :param stream: The uploaded CSV file.
        :param mapping: Which columns hold the date, description and amount.
        :return: How many rows were imported, skipped and rejected.
        :raises AppError: CSV_FILE_TOO_LARGE when the file exceeds the size limit.
        :raises AppError: NOT_FOUND when the account or category is missing or not the user's.
        :raises AppError: INVALID_CSV_MAPPING when a mapped column is not in the header.
        """
        content = await self._read_upload_within_size_limit(stream)
        await self._validate_account_and_category(user_id, account_id, mapping)
        rows, rejected_count = await asyncio.to_thread(
            _parse_csv_rows, content, account_id, mapping
        )
        inserted_count = 0
        if rows:
            async with self._session_factory.get_session() as session:
                inserted_count = await TransactionRepository(
                    session
                ).create_imported_transactions(rows)
        return CSVImportResponseModel(
            imported_count=inserted_count,
            skipped_count=len(rows) - inserted_count,
            rejected_count=rejected_count,
        )

    async def _read_upload_within_size_limit(self, stream: BinaryIO) -> bytes:
        max_file_size_bytes = self._csv_import_settings.max_file_size_bytes
        content = await asyncio.to_thread(stream.read, max_file_size_bytes + 1)
        if len(content) > max_file_size_bytes:
            logger.warning("CSV upload rejected, over %s bytes.", max_file_size_bytes)
            raise AppError(AppErrorCode.CSV_FILE_TOO_LARGE)
        return content

    async def _validate_account_and_category(
        self, user_id: uuid.UUID, account_id: uuid.UUID, mapping: CSVImportMappingModel
    ) -> None:
        async with self._session_factory.get_session() as session:
            account = await AccountRepository(session).get_account_by_id(
                user_id, account_id
            )
            if account is None:
                logger.warning("Import rejected, account_id=%s not found.", account_id)
                raise AppError(AppErrorCode.NOT_FOUND)
            if mapping.category_id is not None:
                category = await CategoryRepository(session).get_category_by_id(
                    user_id, mapping.category_id
                )
                if category is None:
                    logger.warning(
                        "Import rejected, category_id=%s not found.",
                        mapping.category_id,
                    )
                    raise AppError(AppErrorCode.NOT_FOUND)


def _parse_csv_rows(
    content: bytes, account_id: uuid.UUID, mapping: CSVImportMappingModel
) -> tuple[list[dict[str, Any]], int]:
    reader = csv.DictReader(io.StringIO(content.decode(CSV_ENCODING, errors="replace")))
    mapped_columns = {
        mapping.date_column,
        mapping.description_column,
        mapping.amount_column,
    }
    if not mapped_columns.issubset(reader.fieldnames or []):
        logger.warning("Import rejected, mapped column missing from the header.")
        raise AppError(AppErrorCode.INVALID_CSV_MAPPING)
    rows = []
    rejected_count = 0
    for csv_row in reader:
        try:
            booked_on = datetime.strptime(
                (csv_row.get(mapping.date_column) or "").strip(), mapping.date_format
            ).date()
            amount_minor = int(
                (
                    Decimal((csv_row.get(mapping.amount_column) or "").strip())
                    * MINOR_UNITS_PER_MAJOR
                ).to_integral_value()
            )
        except ValueError, ArithmeticError:
            rejected_count += 1
            continue
        description = (csv_row.get(mapping.description_column) or "").strip()
        if (
            amount_minor == 0
            or not MIN_AMOUNT_MINOR <= amount_minor <= MAX_AMOUNT_MINOR
            or len(description) > MAX_DESCRIPTION_LENGTH
        ):
            rejected_count += 1
            continue
        import_hash = hashlib.sha256(
            f"{booked_on.isoformat()}|{amount_minor}|{description}".encode()
        ).hexdigest()
        rows.append(
            {
                "id": uuid.uuid7(),
                "account_id": account_id,
                "category_id": mapping.category_id,
                "amount_minor": amount_minor,
                "booked_on": booked_on,
                "description": description,
                "import_hash": import_hash,
            }
        )
    return rows, rejected_count
