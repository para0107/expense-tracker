import uuid

from expense_tracker.models.base import RequestModel, ResponseModel

DEFAULT_DATE_FORMAT = "%Y-%m-%d"


class CSVImportMappingModel(RequestModel):
    date_column: str
    description_column: str
    amount_column: str
    date_format: str
    category_id: uuid.UUID | None


class CSVImportResponseModel(ResponseModel):
    imported_count: int
    skipped_count: int
    rejected_count: int
