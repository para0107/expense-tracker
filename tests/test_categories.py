from httpx import AsyncClient

from expense_tracker.api.paths import API_PREFIX

CATEGORIES_URL = f"{API_PREFIX}/categories"
NEW_CATEGORY = {"name": "Groceries"}


async def test_category_crud(logged_in_client: AsyncClient) -> None:
    created = await logged_in_client.post(CATEGORIES_URL, json=NEW_CATEGORY)
    assert created.status_code == 201
    category = created.json()
    assert category["name"] == "Groceries"

    fetched = await logged_in_client.get(f"{CATEGORIES_URL}/{category['id']}")
    assert fetched.status_code == 200
    assert fetched.json() == category

    listed = await logged_in_client.get(CATEGORIES_URL)
    assert listed.status_code == 200
    assert listed.json()["items"] == [category]
    assert listed.json()["totalCount"] == 1

    deleted = await logged_in_client.delete(f"{CATEGORIES_URL}/{category['id']}")
    assert deleted.status_code == 204
    missing = await logged_in_client.get(f"{CATEGORIES_URL}/{category['id']}")
    assert missing.status_code == 404


async def test_duplicate_name_is_conflict(logged_in_client: AsyncClient) -> None:
    await logged_in_client.post(CATEGORIES_URL, json=NEW_CATEGORY)
    duplicate = await logged_in_client.post(CATEGORIES_URL, json=NEW_CATEGORY)
    assert duplicate.status_code == 409


async def test_other_user_gets_not_found(
    logged_in_client: AsyncClient, other_logged_in_client: AsyncClient
) -> None:
    created = await logged_in_client.post(CATEGORIES_URL, json=NEW_CATEGORY)
    category_id = created.json()["id"]
    assert (
        await other_logged_in_client.get(f"{CATEGORIES_URL}/{category_id}")
    ).status_code == 404
    assert (
        await other_logged_in_client.delete(f"{CATEGORIES_URL}/{category_id}")
    ).status_code == 404
    assert (await other_logged_in_client.get(CATEGORIES_URL)).json()["items"] == []


async def test_requires_login(client: AsyncClient) -> None:
    response = await client.get(CATEGORIES_URL)
    assert response.status_code == 401
