# expense-tracker

Personal expense tracker API: FastAPI, async SQLAlchemy + asyncpg, PostgreSQL, Alembic. Package `expense_tracker` in `src/`, imported by its bare name.

## Layout
- `src/expense_tracker/schemas/`: SQLAlchemy ORM models (`Base`, `AuditMixin`); register new modules in `schemas/__init__.py`
- `models/`: Pydantic models and enums (`pagination.py` holds the page constants)
- `api/routes/`, `api/dependencies.py`, `api/middleware/` (auth, CSRF), `api/lifespan.py`
- `services/` (business rules, transaction), `repositories/` (data access, filter on `user_id`)
- `exceptions/`, `security/`, `configuration/`, `database/`, `worker/`
- `alembic/versions/`: hand-written migrations `0001`..`0007`
- `tests/`: pytest against a real PostgreSQL

## Commands
- `make sync`, `make lint`, `make format`, `make format-check`
- `make migrate`, `make run-api`, `make run-worker`
- `uv run pytest` (needs `DATABASE__URL` and PostgreSQL: `docker compose -f dev/docker-compose.yml up -d`)

## Conventions
- Tests exist; every endpoint and the worker are covered. Never write `.env`; keep `.env.example` in step with `config.py`.
- `AppErrorCode` members carry `ErrorDetail(code, status, message)`; raise `AppError`, never `HTTPException`.
- Every table extends `AuditMixin` (`created_at`, `updated_at` timestamptz).
- No varchar/char columns: text with a CHECK. Invariants are DB constraints.
- Amounts are signed BIGINT `amount_minor` (negative = expense).
- Ids are `uuid.uuid7()`, set by services.
- Pagination constants live in `models/pagination.py`; a `page_size` over the maximum is a 422.
- Auth: cookie tokens only, Argon2id, rotating refresh tokens in a family.

## Notes kept by cw
- The tool guard blocks Bash commands whose text mentions the env file name inside heredocs; create such files with the Write tool.
- AuthSettings.jwt_secret_key is a SecretStr: read it with .get_secret_value().
- A PostToolUse hook may reformat files written with Write and mis-sort imports (expense_tracker treated as third-party): run `uv run ruff check .` after writes.
- Alembic is async; tests/conftest.py runs `alembic upgrade head` in a sync session fixture, so env.py's asyncio.run has no running loop.
- tests/conftest.py truncates every Base.metadata table after each test, so all tests need DATABASE__URL and a running PostgreSQL.
- tests/ is not a package: share constants through fixtures in conftest, never `from tests.conftest import ...`.
- The ruff PostToolUse hook removes unused imports on each edit: when wiring a new router or provider, add the usage first and the import second.
- The recurring worker runs as `uv run python -m expense_tracker.worker.main`, a separate process from the API; it books every missed occurrence from start_date on its first run, and ON CONFLICT (recurring_transaction_id, booked_on) makes reruns safe.
