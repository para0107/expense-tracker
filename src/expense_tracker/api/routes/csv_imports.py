import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile

from expense_tracker.api.dependencies import CurrentUser, get_csv_import_service
from expense_tracker.exceptions.error_codes import AppErrorCode
from expense_tracker.exceptions.status_codes import AppStatusCode
from expense_tracker.models.csv_import import (
    DEFAULT_DATE_FORMAT,
    CSVImportMappingModel,
    CSVImportResponseModel,
)
from expense_tracker.models.error import ErrorResponseModel
from expense_tracker.services.csv_import_service import CSVImportService

router = APIRouter(prefix="/accounts/{account_id}/imports", tags=["csv-imports"])

CSVImportServiceDependency = Annotated[
    CSVImportService, Depends(get_csv_import_service)
]


@router.post(
    "",
    response_model=CSVImportResponseModel,
    status_code=AppStatusCode.OK,
    responses=ErrorResponseModel.error_response(
        AppErrorCode.UNAUTHORIZED, "The caller is not logged in."
    )
    | ErrorResponseModel.error_response(
        AppErrorCode.NOT_FOUND,
        "The account or category does not exist or is not the caller's.",
    )
    | ErrorResponseModel.error_response(
        AppErrorCode.INVALID_CSV_MAPPING,
        "A mapped column is missing from the CSV header.",
    )
    | ErrorResponseModel.error_response(
        AppErrorCode.CSV_FILE_TOO_LARGE, "The file is over the size limit."
    )
    | ErrorResponseModel.error_response(
        AppErrorCode.VALIDATION_ERROR, "The request is not valid."
    ),
)
async def import_transactions(
    account_id: uuid.UUID,
    current_user: CurrentUser,
    csv_import_service: CSVImportServiceDependency,
    file: Annotated[UploadFile, File(description="The bank export as a CSV file.")],
    date_column: Annotated[str, Form(description="Header of the date column.")],
    description_column: Annotated[
        str, Form(description="Header of the description column.")
    ],
    amount_column: Annotated[
        str,
        Form(
            description="Header of the amount column, in major units, for example -3.50."
        ),
    ],
    date_format: Annotated[
        str, Form(description="strptime format of the dates.")
    ] = DEFAULT_DATE_FORMAT,
    category_id: Annotated[
        uuid.UUID | None,
        Form(description="Category given to every imported transaction."),
    ] = None,
) -> CSVImportResponseModel:
    """
    Import a bank export into one of the logged-in user's accounts.
    """
    mapping = CSVImportMappingModel(
        date_column=date_column,
        description_column=description_column,
        amount_column=amount_column,
        date_format=date_format,
        category_id=category_id,
    )
    return await csv_import_service.import_transactions(
        current_user.id, account_id, file.file, mapping
    )
