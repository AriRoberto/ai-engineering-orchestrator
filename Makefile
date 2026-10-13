.PHONY: install run test lint compose-up compose-down

install:
	python -m pip install -e '.[dev]'

run:
	uvicorn apps.api.main:app --reload

test:
	pytest

lint:
	ruff check .

compose-up:
	docker compose up --build

compose-down:
	docker compose down

