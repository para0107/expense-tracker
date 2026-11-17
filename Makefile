.PHONY: sync lint format format-check migrate run-api run-worker

sync:
	uv sync

lint:
	uv run ruff check .

format:
	uv run ruff format .

format-check:
	uv run ruff format --check .

migrate:
	PYTHONPATH=. uv run alembic upgrade head

run-api:
	uv run uvicorn expense_tracker.api.app:app --reload

run-worker:
	uv run python -m expense_tracker.worker.main
