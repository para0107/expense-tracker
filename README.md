# expense-tracker

A personal expense tracker REST API built with FastAPI, async SQLAlchemy (asyncpg), PostgreSQL and Alembic.

## Features

- Accounts (name, currency), categories, and tags on transactions (many to many)
- Transactions (account, category, tags, amount in minor units, date, description) with filters by date range, account, category and tag, and pagination
- Monthly budgets per category reporting spent, remaining and whether the budget is exceeded
- Recurring transactions (monthly or weekly rules) booked once per period by a separate scheduled worker, without duplicates on reruns
- CSV import of a bank export with a column mapping (date, description, amount); reports imported, skipped and rejected rows
- Monthly report: income, expenses, totals per category and the top five descriptions by spending
- Health endpoint that checks the database
- Cookie-based authentication with access and refresh tokens

## Setup

```bash
uv sync
docker compose -f dev/docker-compose.yml up -d
```

Create `.env` yourself from `.env.example` and fill every key (including `DATABASE__URL`, for example `postgresql+asyncpg://expense_tracker:expense_tracker@localhost:5432/expense_tracker`). The app never writes `.env`.

```bash
make migrate     # alembic upgrade head
make run-api     # uvicorn expense_tracker.api.app:app --reload
make run-worker  # python -m expense_tracker.worker.main
```

The API and the recurring worker are separate processes. On its first run the worker books every missed occurrence from the rule's `start_date`; a monthly rule starting on the 31st is clamped to the last day of shorter months.

## Lint and tests

```bash
uv run ruff check .
uv run pytest
```

Tests need `DATABASE__URL` pointing at a disposable PostgreSQL database: the schema is created with the Alembic migrations and every table is truncated after each test. Tests set every other setting themselves and never read `.env`.

## Authentication

Tokens are only ever sent as `httpOnly`, `Secure`, `SameSite=Strict` cookies, never in a response body.

| Cookie | Lifetime | Path |
|---|---|---|
| access token (claim `type: access`) | 15 minutes | `/api/v1` |
| refresh token | 7 days | `/api/v1/auth/refresh` |

Flow under `/api/v1/auth`:

- `register`: create a user (Argon2id password hash)
- `login`: sets both cookies; a wrong password and an unknown email give the same 401
- `refresh`: rotates the refresh token within its family; presenting a revoked token revokes the whole family
- `logout`: revokes the session family and clears the cookies

Refresh tokens are stored as SHA-256 hashes. A CSRF middleware rejects unsafe methods (POST, PUT, PATCH, DELETE) whose `Origin` or `Sec-Fetch-Site` indicates a cross-site request.

Public registration is a named deviation from the team's security rules, accepted for a personal app.
