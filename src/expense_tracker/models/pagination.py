from math import ceil
from typing import Self

from expense_tracker.models.base import ResponseModel

DEFAULT_PAGE = 1
MIN_PAGE = 1
DEFAULT_PAGE_SIZE = 20
MIN_PAGE_SIZE = 1
MAX_PAGE_SIZE = 100


class PageResponseModel[T](ResponseModel):
    items: list[T]
    page: int
    page_size: int
    total_count: int
    total_pages: int

    @classmethod
    def create(
        cls, items: list[T], page: int, page_size: int, total_count: int
    ) -> Self:
        return cls(
            items=items,
            page=page,
            page_size=page_size,
            total_count=total_count,
            total_pages=ceil(total_count / page_size),
        )
