from httpx import AsyncClient

from expense_tracker.api.paths import (
    ACCESS_TOKEN_COOKIE_NAME,
    API_PREFIX,
    REFRESH_TOKEN_COOKIE_NAME,
)

TEST_PASSWORD = "correct horse battery"
AUTH_URL = f"{API_PREFIX}/auth"
EMAIL = "person@example.com"
CREDENTIALS = {"email": EMAIL, "password": TEST_PASSWORD}


async def test_login_sets_secure_cookies_and_no_token_in_body(
    client: AsyncClient,
) -> None:
    await client.post(f"{AUTH_URL}/register", json=CREDENTIALS)

    response = await client.post(f"{AUTH_URL}/login", json=CREDENTIALS)

    assert response.status_code == 200
    assert set(response.json()) == {"id", "email"}
    set_cookies = response.headers.get_list("set-cookie")
    assert len(set_cookies) == 2
    for cookie, name in zip(
        sorted(set_cookies), (ACCESS_TOKEN_COOKIE_NAME, REFRESH_TOKEN_COOKIE_NAME)
    ):
        assert cookie.startswith(name)
        assert "HttpOnly" in cookie and "Secure" in cookie
        assert "SameSite=strict" in cookie


async def test_me_needs_cookies(
    logged_in_client: AsyncClient, client: AsyncClient
) -> None:
    assert (await logged_in_client.get(f"{AUTH_URL}/me")).json()["email"] == (
        "user-a@example.com"
    )
    assert (await client.get(f"{AUTH_URL}/me")).status_code == 401


async def test_refresh_rotates(logged_in_client: AsyncClient) -> None:
    before = logged_in_client.cookies.get(REFRESH_TOKEN_COOKIE_NAME)

    response = await logged_in_client.post(f"{AUTH_URL}/refresh")

    assert response.status_code == 204
    assert logged_in_client.cookies.get(REFRESH_TOKEN_COOKIE_NAME) != before
    assert (await logged_in_client.get(f"{AUTH_URL}/me")).status_code == 200


async def test_logout_then_refresh_fails(logged_in_client: AsyncClient) -> None:
    refresh_token = logged_in_client.cookies.get(REFRESH_TOKEN_COOKIE_NAME)

    assert (await logged_in_client.post(f"{AUTH_URL}/logout")).status_code == 204

    response = await logged_in_client.post(
        f"{AUTH_URL}/refresh",
        headers={"Cookie": f"{REFRESH_TOKEN_COOKIE_NAME}={refresh_token}"},
    )
    assert response.status_code == 401


async def test_wrong_password_and_unknown_email_look_the_same(
    client: AsyncClient,
) -> None:
    await client.post(f"{AUTH_URL}/register", json=CREDENTIALS)

    wrong_password = await client.post(
        f"{AUTH_URL}/login", json={"email": EMAIL, "password": "wrong-password"}
    )
    unknown_email = await client.post(
        f"{AUTH_URL}/login",
        json={"email": "nobody@example.com", "password": TEST_PASSWORD},
    )

    assert wrong_password.status_code == unknown_email.status_code == 401
    assert wrong_password.json() == unknown_email.json()


async def test_cross_site_post_is_rejected(client: AsyncClient) -> None:
    for headers in (
        {"Origin": "https://evil.example"},
        {"Sec-Fetch-Site": "cross-site"},
    ):
        response = await client.post(
            f"{AUTH_URL}/login", json=CREDENTIALS, headers=headers
        )
        assert response.status_code == 403
