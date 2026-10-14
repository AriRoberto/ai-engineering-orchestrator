.PHONY: install run test lint compose-up compose-down

install:
	python -m pip install -e '.[dev]'

run:
	python -m uvicorn apps.api.main:app --reload

test:
	python -m pytest

lint:
	python -m ruff check .

compose-up:
	docker compose up --build

compose-down:
	docker compose down

