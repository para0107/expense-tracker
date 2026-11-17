import pytest

from expense_tracker.models.pagination import PageResponseModel


@pytest.mark.parametrize(
    ("total_count", "expected_total_pages"), [(0, 0), (40, 2), (41, 3)]
)
def test_create_computes_total_pages(total_count, expected_total_pages):
    page = PageResponseModel[int].create([], 1, 20, total_count)

    assert page.total_pages == expected_total_pages
