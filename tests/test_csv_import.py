from httpx import AsyncClient

from expense_tracker.api.paths import API_PREFIX
from expense_tracker.exceptions.error_codes import AppErrorCode

ACCOUNTS_URL = f"{API_PREFIX}/accounts"
TRANSACTIONS_URL = f"{API_PREFIX}/transactions"
CATEGORIES_URL = f"{API_PREFIX}/categories"
OVER_LIMIT_BYTES = 1048576 + 1
MAPPING = {
    "date_column": "date",
    "description_column": "description",
    "amount_column": "amount",
}
MIXED_CSV = (
    "date,description,amount\n"
    "2026-01-05,Coffee,-3.50\n"
    "2026-01-06,Salary,1000.00\n"
    "bad-date,Oops,1.00\n"
    "2026-01-07,Zero,0\n"
    "2026-01-08,Letters,abc\n"
)


async def create_account_id(client: AsyncClient) -> str:
    response = await client.post(
        ACCOUNTS_URL, json={"name": "Checking", "currency": "EUR"}
    )
    return response.json()["id"]


async def import_csv(
    client: AsyncClient, account_id: str, content: bytes | str, **form: str
) -> object:
    return await client.post(
        f"{ACCOUNTS_URL}/{account_id}/imports",
        files={"file": ("bank.csv", content, "text/csv")},
        data=MAPPING | form,
    )


async def test_mixed_file_reports_counts_and_stores_amounts(
    logged_in_client: AsyncClient,
) -> None:
    account_id = await create_account_id(logged_in_client)

    response = await import_csv(logged_in_client, account_id, MIXED_CSV)

    assert response.status_code == 200
    assert response.json() == {
        "importedCount": 2,
        "skippedCount": 0,
        "rejectedCount": 3,
    }
    listed = await logged_in_client.get(TRANSACTIONS_URL)
    assert [item["amountMinor"] for item in listed.json()["items"]] == [100000, -350]


async def test_same_file_twice_skips_everything(
    logged_in_client: AsyncClient,
) -> None:
    account_id = await create_account_id(logged_in_client)
    await import_csv(logged_in_client, account_id, MIXED_CSV)

    response = await import_csv(logged_in_client, account_id, MIXED_CSV)

    assert response.json() == {
        "importedCount": 0,
        "skippedCount": 2,
        "rejectedCount": 3,
    }
    listed = await logged_in_client.get(TRANSACTIONS_URL)
    assert listed.json()["totalCount"] == 2


async def test_custom_columns_date_format_and_category(
    logged_in_client: AsyncClient,
) -> None:
    account_id = await create_account_id(logged_in_client)
    category = await logged_in_client.post(CATEGORIES_URL, json={"name": "Bank"})
    category_id = category.json()["id"]

    response = await import_csv(
        logged_in_client,
        account_id,
        "Booked;Text;Sum\n",
        date_column="Booked",
        description_column="Text",
        amount_column="Sum",
        date_format="%d.%m.%Y",
        category_id=category_id,
    )
    assert response.status_code == 400

    response = await import_csv(
        logged_in_client,
        account_id,
        "Booked,Text,Sum\n05.01.2026,Rent,-12.5\n",
        date_column="Booked",
        description_column="Text",
        amount_column="Sum",
        date_format="%d.%m.%Y",
        category_id=category_id,
    )
    assert response.json()["importedCount"] == 1
    listed = await logged_in_client.get(
        TRANSACTIONS_URL, params={"category_id": category_id}
    )
    item = listed.json()["items"][0]
    assert item["amountMinor"] == -1250
    assert item["bookedOn"] == "2026-01-05"


async def test_missing_mapped_column_is_bad_request(
    logged_in_client: AsyncClient,
) -> None:
    account_id = await create_account_id(logged_in_client)

    response = await import_csv(
        logged_in_client, account_id, MIXED_CSV, amount_column="missing"
    )

    assert response.status_code == 400
    detail = AppErrorCode.INVALID_CSV_MAPPING.value
    assert response.json() == {
        "code": detail.code,
        "status": detail.status,
        "message": detail.message,
    }


async def test_oversized_file_is_rejected(logged_in_client: AsyncClient) -> None:
    account_id = await create_account_id(logged_in_client)

    response = await import_csv(logged_in_client, account_id, b"x" * OVER_LIMIT_BYTES)

    assert response.status_code == 413
    assert response.json()["code"] == "CSV_FILE_TOO_LARGE"


async def test_other_users_account_and_category_are_not_found(
    logged_in_client: AsyncClient, other_logged_in_client: AsyncClient
) -> None:
    account_id = await create_account_id(logged_in_client)
    own_account_id = await create_account_id(other_logged_in_client)
    category = await logged_in_client.post(CATEGORIES_URL, json={"name": "Mine"})

    foreign_account = await import_csv(other_logged_in_client, account_id, MIXED_CSV)
    foreign_category = await import_csv(
        other_logged_in_client,
        own_account_id,
        MIXED_CSV,
        category_id=category.json()["id"],
    )

    assert foreign_account.status_code == 404
    assert foreign_category.status_code == 404


async def test_requires_login(client: AsyncClient) -> None:
    response = await client.post(
        f"{ACCOUNTS_URL}/00000000-0000-0000-0000-000000000000/imports",
        files={"file": ("bank.csv", MIXED_CSV, "text/csv")},
        data=MAPPING,
    )
    assert response.status_code == 401
