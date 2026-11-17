from httpx import AsyncClient

from expense_tracker.api.paths import API_PREFIX

TAGS_URL = f"{API_PREFIX}/tags"
NEW_TAG = {"name": "holiday"}


async def test_tag_crud(logged_in_client: AsyncClient) -> None:
    created = await logged_in_client.post(TAGS_URL, json=NEW_TAG)
    assert created.status_code == 201
    tag = created.json()
    assert tag["name"] == "holiday"

    fetched = await logged_in_client.get(f"{TAGS_URL}/{tag['id']}")
    assert fetched.status_code == 200
    assert fetched.json() == tag

    listed = await logged_in_client.get(TAGS_URL)
    assert listed.status_code == 200
    assert listed.json()["items"] == [tag]
    assert listed.json()["totalCount"] == 1

    deleted = await logged_in_client.delete(f"{TAGS_URL}/{tag['id']}")
    assert deleted.status_code == 204
    missing = await logged_in_client.get(f"{TAGS_URL}/{tag['id']}")
    assert missing.status_code == 404


async def test_duplicate_name_is_conflict(logged_in_client: AsyncClient) -> None:
    await logged_in_client.post(TAGS_URL, json=NEW_TAG)
    duplicate = await logged_in_client.post(TAGS_URL, json=NEW_TAG)
    assert duplicate.status_code == 409


async def test_other_user_gets_not_found(
    logged_in_client: AsyncClient, other_logged_in_client: AsyncClient
) -> None:
    created = await logged_in_client.post(TAGS_URL, json=NEW_TAG)
    tag_id = created.json()["id"]
    assert (await other_logged_in_client.get(f"{TAGS_URL}/{tag_id}")).status_code == 404
    assert (
        await other_logged_in_client.delete(f"{TAGS_URL}/{tag_id}")
    ).status_code == 404
    assert (await other_logged_in_client.get(TAGS_URL)).json()["items"] == []


async def test_requires_login(client: AsyncClient) -> None:
    response = await client.get(TAGS_URL)
    assert response.status_code == 401
