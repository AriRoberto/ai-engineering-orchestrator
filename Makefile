.PHONY: install run test lint compose-up compose-up-detached compose-down logs verificar lab-fase2 lab-fase3

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

compose-up-detached:
	docker compose up --build -d

compose-down:
	docker compose down

logs:
	docker compose logs --tail=100 api postgres

verificar:
	./scripts/verificar-ambiente.sh

lab-fase2:
	./scripts/laboratorio-fase2.sh

lab-fase3:
	./scripts/laboratorio-fase3.sh

