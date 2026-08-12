.PHONY: up down reset migrate seed dev test lint fmt

up:
	docker compose up -d

down:
	docker compose down

reset:
	docker compose down -v
	docker compose up -d

migrate:
	uv run alembic upgrade head

seed:
	uv run python -m scripts.seed

dev:
	uv run uvicorn app.main:app --reload

test:
	uv run pytest

lint:
	uv run ruff check .

fmt:
	uv run ruff format .
