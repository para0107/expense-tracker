from typing import Annotated

from fastapi import APIRouter, Depends

from expense_tracker.api.dependencies import get_health_service
from expense_tracker.exceptions.error_codes import AppErrorCode
from expense_tracker.exceptions.status_codes import AppStatusCode
from expense_tracker.models.error import ErrorResponseModel
from expense_tracker.models.health import HealthResponseModel
from expense_tracker.services.health_service import HealthService

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    response_model=HealthResponseModel,
    status_code=AppStatusCode.OK,
    responses=ErrorResponseModel.error_response(
        AppErrorCode.DATABASE_UNAVAILABLE, "The database does not answer."
    ),
)
async def get_health(
    health_service: Annotated[HealthService, Depends(get_health_service)],
) -> HealthResponseModel:
    """
    Check that the API is up and the database answers.
    """
    await health_service.check_database()
    return HealthResponseModel(status="ok")
