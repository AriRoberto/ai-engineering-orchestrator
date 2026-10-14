# Laboratório guiado — Fase 1

Os exercícios usam somente nomes de arquivos fictícios. Os agentes da Fase 1 não acessam esses
arquivos: analisam a lista fornecida em `context.files` e marcam o resultado como simulado.

## Preparação

```bash
docker compose up --build -d
curl http://localhost:8000/health
```

Em outro terminal, acompanhe os logs:

```bash
docker compose logs -f api
```

## Exercício 1 — Software Engineering Agent

### Objetivo

Verificar a seleção do agente de software e a detecção simples de uma stack fictícia a partir de
manifestos conhecidos.

### Requisição

```bash
curl -sS -X POST http://localhost:8000/v1/executions \
  -H 'Content-Type: application/json' \
  -d '{
    "project_id": "demo-loja",
    "prompt": "Analise o código e identifique a stack de software",
    "read_only": true,
    "demo": true,
    "context": {"files": ["pyproject.toml", "package.json", "src/exemplo.py"]}
  }'
```

### Parâmetros

- `project_id`: identificador fictício isolado da execução;
- `prompt`: contém `código`, `stack` e `software`, que roteiam para Software Engineering;
- `read_only`: impede qualquer fluxo de escrita;
- `demo`: marca cada resultado com `simulated: true`;
- `context.files`: evidências declaradas, não caminhos que a API abrirá.

### Resultado esperado e interpretação

O HTTP status será `201`. `status` deve ser `COMPLETED`, `selected_agents` deve conter
`software-engineer`, e `findings` deve informar Python e JavaScript/TypeScript. Em `evidence`, apenas
os manifestos reconhecidos aparecem; `src/exemplo.py` não é inspecionado.

Isso comprova roteamento e reconhecimento por assinatura, não análise real de código.

### Logs

No terminal de logs, procure `event=execution_processed` (em JSON, `"event":
"execution_processed"`), o UUID e `"execution_status":"COMPLETED"`.

## Exercício 2 — DevOps Agent

### Objetivo

Simular um diagnóstico da presença de container e workflow de CI.

### Requisição

```bash
curl -sS -X POST http://localhost:8000/v1/executions \
  -H 'Content-Type: application/json' \
  -d '{
    "project_id": "demo-pipeline",
    "prompt": "Faça um diagnóstico DevOps do Docker e pipeline CI/CD",
    "read_only": true,
    "demo": true,
    "context": {"files": ["Dockerfile", ".github/workflows/ci.yml", "README.md"]}
  }'
```

### Parâmetros

O texto contém `docker`, `pipeline` e `ci/cd`, selecionando DevOps. A lista fictícia inclui os dois
nomes que o agente reconhece: `Dockerfile` e um caminho iniciado por `.github/workflows/`.

### Resultado esperado e interpretação

`selected_agents` deve conter `devops`. Os achados esperados são `Container definition found` e
`GitHub Actions workflow found`. O agente apenas confirma nomes na entrada; ele não abre o
Dockerfile, valida YAML, executa pipeline ou consulta GitHub.

### Logs

```bash
docker compose logs --tail=20 api
```

Compare o `execution_id` da resposta com o ID exibido no log estruturado.

## Exercício 3 — Kubernetes Agent

### Objetivo

Simular a identificação de evidências Kubernetes/Helm.

### Requisição

```bash
curl -sS -X POST http://localhost:8000/v1/executions \
  -H 'Content-Type: application/json' \
  -d '{
    "project_id": "demo-kubernetes",
    "prompt": "Diagnostique o deployment Kubernetes e o chart Helm",
    "read_only": true,
    "demo": true,
    "context": {"files": ["k8s/deployment.yaml", "helm/values.yaml", "Chart.yaml"]}
  }'
```

### Parâmetros

`kubernetes`, `deployment` e `helm` selecionam o agente. Os três itens de `context.files` atendem às
regras simples de reconhecimento atuais.

### Resultado esperado e interpretação

`selected_agents` deve conter `kubernetes`. O resultado deve indicar `3 Kubernetes/Helm evidence
item(s) supplied`, repetir os três itens em `evidence` e apresentar `simulated: true`.

Isso não valida schema Kubernetes, recursos, namespace, segurança ou capacidade do cluster.

### Logs

```bash
docker compose logs --since=5m api
```

O log confirma que a API processou a execução; detalhes dos achados ficam na resposta HTTP e no
repositório em memória, consultável enquanto o processo estiver ativo:

```bash
curl -sS http://localhost:8000/v1/executions
```

Ao terminar:

```bash
docker compose down
```

