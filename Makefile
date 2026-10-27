.PHONY: install run test lint compose-up compose-up-detached compose-down logs verificar demo lab-fase2 lab-fase3 lab-fase4 lab-fase4-privado eval-fase4 lab-fase5-observabilidade lab-fase5-acesso lab-fase5-kubernetes lab-homologacao lab-kubernetes-local lab-kubernetes-local-down validar-release regressao-static regressao regressao-full

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

demo:
	./scripts/demo-projeto.sh --repository "$(or $(REPOSITORY),AriRoberto/app-financas)" $(if $(PROJECT_ID),--project-id "$(PROJECT_ID)",) $(if $(BRANCH),--branch "$(BRANCH)",) $(if $(PROMPT),--prompt "$(PROMPT)",)

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

lab-homologacao:
	./scripts/laboratorio-homologacao.sh

lab-kubernetes-local:
	./scripts/laboratorio-kubernetes-local.sh

lab-kubernetes-local-down:
	./scripts/remover-kubernetes-local.sh

validar-release:
	python3 scripts/validar-release.py

regressao-static:
	./scripts/gate-regressao.sh --static

regressao:
	./scripts/gate-regressao.sh --local

regressao-full:
	./scripts/gate-regressao.sh --full

