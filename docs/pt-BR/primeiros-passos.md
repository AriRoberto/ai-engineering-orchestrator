# Primeiros passos no macOS Apple Silicon

Este tutorial executa a Fase 1 localmente, sem credenciais de LLM e sem acessar os projetos pilotos.

## 1. Pré-requisitos

- macOS em Apple Silicon (M1, M2, M3, M4 ou posterior);
- Git;
- Docker Desktop com Docker Compose;
- opcionalmente Python 3.12 para execução fora do container.

Confirme o ambiente:

```bash
git --version
docker --version
docker compose version
```

O Python fornecido por versões antigas do macOS pode ser 3.9. Use o container ou instale Python
3.12; o projeto declara `requires-python = ">=3.12"`.

## 2. Obter o projeto

```bash
git clone https://github.com/AriRoberto/ai-engineering-orchestrator.git
cd ai-engineering-orchestrator
git switch develop
```

Para apenas testar a versão publicada, `main` também pode ser usada. Mudanças devem partir de
`develop` em uma branch no padrão documentado em `CONTRIBUTING.md`.

## 3. Configurar o `.env`

```bash
cp .env.example .env
```

Conteúdo disponível:

```dotenv
AIEO_ENVIRONMENT=development
AIEO_LOG_LEVEL=INFO
AIEO_DEMO_MODE=true
AIEO_MAX_STEPS=8
AIEO_AGENT_TIMEOUT_SECONDS=5
AIEO_MAX_RETRIES=1
```

Não inclua tokens no `.env`. A Fase 1 não precisa deles. O arquivo é ignorado pelo Git.

Observação: o `compose.yaml` define ambiente e modo demo diretamente. As demais variáveis usam os
valores padrão da aplicação, a menos que sejam adicionadas ao bloco `environment` do serviço.

## 4. Iniciar com Docker Compose

Certifique-se de que o Docker Desktop esteja aberto. No diretório do projeto:

```bash
docker compose up --build -d
docker compose ps
```

O serviço deve aparecer como `Up`. O health check pode mostrar `starting` nos primeiros segundos.
Valide a API:

```bash
curl http://localhost:8000/health
```

Resposta esperada:

```json
{"status":"healthy","service":"ai-engineering-orchestrator"}
```

## 5. Acessar Swagger e OpenAPI

Abra no navegador:

- Swagger UI: <http://localhost:8000/docs>
- schema OpenAPI: <http://localhost:8000/openapi.json>

No Swagger, expanda `POST /v1/executions`, clique em **Try it out**, informe um JSON fictício e
clique em **Execute**.

## 6. Inicializar a API sem Docker

Com Python 3.12 instalado:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
python -m uvicorn apps.api.main:app --reload
```

Mantenha esse terminal aberto. A API ficará em <http://localhost:8000>.

## 7. Verificar logs

Para acompanhar o serviço do Compose:

```bash
docker compose logs -f api
```

Após enviar uma execução, procure um JSON semelhante a:

```json
{"execution_id":"<uuid>","execution_status":"COMPLETED","event":"execution_processed"}
```

Use `Control+C` para sair do acompanhamento; isso não interrompe o container.

## 8. Executar lint e testes

Com Python 3.12 local e o ambiente virtual ativado:

```bash
python -m ruff check .
python -m pytest
```

O uso de `python -m pytest` é o padrão do projeto e também é usado pela CI.

Para testar no container de runtime sem depender do Python do Mac:

```bash
docker build -t ai-engineering-orchestrator:phase1 .
docker run --rm \
  -e COVERAGE_FILE=/tmp/.coverage \
  -v "$PWD:/workspace:ro" \
  -w /workspace \
  ai-engineering-orchestrator:phase1 \
  sh -c "pip install '.[dev]' >/tmp/install.log && python -m ruff check --no-cache . && python -m pytest -p no:cacheprovider"
```

## 9. Interromper a stack

```bash
docker compose down
```

Esse comando remove os containers e a rede do Compose. Não há volume persistente na Fase 1.

## 10. Solução de problemas

### Não foi possível conectar ao mecanismo do Docker

Abra o Docker Desktop, aguarde o mecanismo iniciar e execute `docker info`.

### Porta 8000 já está em uso

Descubra o processo:

```bash
lsof -nP -iTCP:8000 -sTCP:LISTEN
```

Interrompa o serviço conhecido ou mude o mapeamento em `compose.yaml`, por exemplo para
`"8001:8000"`, e acesse `http://localhost:8001`.

### Imagem incompatível com Apple Silicon

A imagem oficial `python:3.12-slim` possui suporte ARM64. Remova qualquer `platform: linux/amd64`
adicionado localmente e reconstrua:

```bash
docker compose build --no-cache
```

### Erro `ModuleNotFoundError: apps`

Execute os comandos a partir da raiz do repositório e prefira:

```bash
python -m pytest
python -m uvicorn apps.api.main:app --reload
```

### Health check permanece `starting` ou fica `unhealthy`

```bash
docker compose ps
docker compose logs --tail=100 api
curl -v http://localhost:8000/health
```

Confirme que a porta está livre e que o build terminou sem erro.

### Alterações no `.env` não aparecem no Compose

O serviço declara variáveis próprias em `compose.yaml`. Confira a configuração resolvida com:

```bash
docker compose config
```

Adicione explicitamente a variável necessária ao bloco `environment` e recrie o container. Nunca
adicione segredos ao arquivo versionado.

