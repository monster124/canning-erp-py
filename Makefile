.PHONY: run test lint format typecheck check

run:
	uv run uvicorn canning_erp.interfaces.http.app:create_app --factory --reload

test:
	uv run pytest -q

lint:
	uv run ruff check . && uv run ruff format --check .

format:
	uv run ruff format . && uv run ruff check --fix .

typecheck:
	uv run mypy

check: lint typecheck test
