.PHONY: install run test lint compose-up compose-up-detached compose-down logs verificar lab-fase2 lab-fase3 lab-fase4 lab-fase4-privado eval-fase4 lab-fase5-observabilidade lab-fase5-acesso lab-fase5-kubernetes validar-release

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

lab-fase4:
	./scripts/laboratorio-fase4.sh

lab-fase4-privado:
	./scripts/laboratorio-fase4-privado.sh

eval-fase4:
	docker run --rm -v "$(CURDIR):/workspace" -w /workspace ai-engineering-orchestrator:latest \
		sh -c "PYTHONPATH=src python scripts/avaliar-seguranca-evidencias.py"

lab-fase5-observabilidade:
	./scripts/laboratorio-fase5-observabilidade.sh

lab-fase5-acesso:
	./scripts/laboratorio-fase5-acesso.sh

lab-fase5-kubernetes:
	./scripts/laboratorio-fase5-kubernetes.sh

validar-release:
	python3 scripts/validar-release.py

