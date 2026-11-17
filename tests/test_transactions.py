import uuid

from httpx import AsyncClient

from expense_tracker.api.paths import API_PREFIX

TRANSACTIONS_URL = f"{API_PREFIX}/transactions"
ACCOUNTS_URL = f"{API_PREFIX}/accounts"
CATEGORIES_URL = f"{API_PREFIX}/categories"
TAGS_URL = f"{API_PREFIX}/tags"


async def create_id(client: AsyncClient, url: str, body: dict) -> str:
    response = await client.post(url, json=body)
    assert response.status_code == 201
    return response.json()["id"]


async def create_account_id(client: AsyncClient, name: str = "Checking") -> str:
    return await create_id(client, ACCOUNTS_URL, {"name": name, "currency": "EUR"})


async def create_transaction(
    client: AsyncClient, account_id: str, **overrides: object
) -> dict:
    body = {
        "accountId": account_id,
        "amountMinor": -500,
        "bookedOn": "2026-01-10",
        "description": "Coffee",
    } | overrides
    response = await client.post(TRANSACTIONS_URL, json=body)
    assert response.status_code == 201
    return response.json()


async def test_create_with_tags_then_get_and_delete(
    logged_in_client: AsyncClient,
) -> None:
    account_id = await create_account_id(logged_in_client)
    category_id = await create_id(logged_in_client, CATEGORIES_URL, {"name": "Food"})
    tag_id = await create_id(logged_in_client, TAGS_URL, {"name": "treat"})

    transaction = await create_transaction(
        logged_in_client, account_id, categoryId=category_id, tagIds=[tag_id, tag_id]
    )
    assert transaction["amountMinor"] == -500
    assert transaction["categoryId"] == category_id
    assert [tag["id"] for tag in transaction["tags"]] == [tag_id]

    url = f"{TRANSACTIONS_URL}/{transaction['id']}"
    fetched = await logged_in_client.get(url)
    assert fetched.status_code == 200
    assert fetched.json() == transaction

    assert (await logged_in_client.delete(url)).status_code == 204
    assert (await logged_in_client.get(url)).status_code == 404


async def test_filters(logged_in_client: AsyncClient) -> None:
    checking_id = await create_account_id(logged_in_client, "Checking")
    savings_id = await create_account_id(logged_in_client, "Savings")
    food_id = await create_id(logged_in_client, CATEGORIES_URL, {"name": "Food"})
    tag_id = await create_id(logged_in_client, TAGS_URL, {"name": "treat"})
    january = await create_transaction(
        logged_in_client, checking_id, bookedOn="2026-01-10", categoryId=food_id
    )
    february = await create_transaction(
        logged_in_client, checking_id, bookedOn="2026-02-10", tagIds=[tag_id]
    )
    march = await create_transaction(
        logged_in_client, savings_id, bookedOn="2026-03-10"
    )

    async def list_ids(**params: str) -> list[str]:
        response = await logged_in_client.get(TRANSACTIONS_URL, params=params)
        assert response.status_code == 200
        return [item["id"] for item in response.json()["items"]]

    assert await list_ids() == [march["id"], february["id"], january["id"]]
    assert await list_ids(date_from="2026-02-01") == [march["id"], february["id"]]
    assert await list_ids(date_to="2026-02-28") == [february["id"], january["id"]]
    assert await list_ids(account_id=savings_id) == [march["id"]]
    assert await list_ids(category_id=food_id) == [january["id"]]
    assert await list_ids(tag_id=tag_id) == [february["id"]]


async def test_pagination_totals(logged_in_client: AsyncClient) -> None:
    account_id = await create_account_id(logged_in_client)
    for day in range(1, 4):
        await create_transaction(
            logged_in_client, account_id, bookedOn=f"2026-01-0{day}"
        )

    response = await logged_in_client.get(
        TRANSACTIONS_URL, params={"page": 2, "page_size": 2}
    )
    body = response.json()
    assert len(body["items"]) == 1
    assert body["page"] == 2
    assert body["totalCount"] == 3
    assert body["totalPages"] == 2


async def test_page_size_over_maximum_is_rejected(
    logged_in_client: AsyncClient,
) -> None:
    response = await logged_in_client.get(TRANSACTIONS_URL, params={"page_size": 101})
    assert response.status_code == 422


async def test_zero_amount_is_rejected(logged_in_client: AsyncClient) -> None:
    account_id = await create_account_id(logged_in_client)
    response = await logged_in_client.post(
        TRANSACTIONS_URL,
        json={
            "accountId": account_id,
            "amountMinor": 0,
            "bookedOn": "2026-01-10",
            "description": "Nothing",
        },
    )
    assert response.status_code == 422


async def test_foreign_account_category_and_tag_are_not_found(
    logged_in_client: AsyncClient, other_logged_in_client: AsyncClient
) -> None:
    own_account_id = await create_account_id(logged_in_client)
    foreign_account_id = await create_account_id(other_logged_in_client)
    foreign_category_id = await create_id(
        other_logged_in_client, CATEGORIES_URL, {"name": "Food"}
    )
    foreign_tag_id = await create_id(other_logged_in_client, TAGS_URL, {"name": "x"})
    base = {"amountMinor": -1, "bookedOn": "2026-01-10", "description": "x"}

    for body in (
        base | {"accountId": foreign_account_id},
        base | {"accountId": own_account_id, "categoryId": foreign_category_id},
        base | {"accountId": own_account_id, "tagIds": [foreign_tag_id]},
        base | {"accountId": own_account_id, "tagIds": [str(uuid.uuid7())]},
    ):
        response = await logged_in_client.post(TRANSACTIONS_URL, json=body)
        assert response.status_code == 404


async def test_deleting_account_with_transactions_is_conflict(
    logged_in_client: AsyncClient,
) -> None:
    account_id = await create_account_id(logged_in_client)
    await create_transaction(logged_in_client, account_id)
    response = await logged_in_client.delete(f"{ACCOUNTS_URL}/{account_id}")
    assert response.status_code == 409


async def test_deleting_category_in_use_is_conflict(
    logged_in_client: AsyncClient,
) -> None:
    account_id = await create_account_id(logged_in_client)
    category_id = await create_id(logged_in_client, CATEGORIES_URL, {"name": "Food"})
    await create_transaction(logged_in_client, account_id, categoryId=category_id)
    response = await logged_in_client.delete(f"{CATEGORIES_URL}/{category_id}")
    assert response.status_code == 409


async def test_other_user_cannot_see_transaction(
    logged_in_client: AsyncClient, other_logged_in_client: AsyncClient
) -> None:
    account_id = await create_account_id(logged_in_client)
    transaction = await create_transaction(logged_in_client, account_id)
    url = f"{TRANSACTIONS_URL}/{transaction['id']}"

    assert (await other_logged_in_client.get(url)).status_code == 404
    assert (await other_logged_in_client.delete(url)).status_code == 404
    listed = await other_logged_in_client.get(TRANSACTIONS_URL)
    assert listed.json()["items"] == []
    assert (await logged_in_client.get(url)).status_code == 200


async def test_requires_login(client: AsyncClient) -> None:
    response = await client.get(TRANSACTIONS_URL)
    assert response.status_code == 401
