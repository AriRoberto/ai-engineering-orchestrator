# Roteiro de validação do projeto `app-financas`

Este roteiro valida o estado atual do AI Engineering Orchestrator usando o repositório público
[`AriRoberto/app-financas`](https://github.com/AriRoberto/app-financas).

## O que este teste faz

O Orquestrador consulta a API do GitHub, lê o inventário e um conjunto limitado de arquivos
textuais do `app-financas`, executa os especialistas e registra o diagnóstico e sua proveniência.

Este teste **não inicia a aplicação `app-financas`**, não executa seu código e não modifica seu
repositório. Também não cria branch, commit ou Pull Request. Todo acesso ao GitHub é somente leitura.

O servidor MCP real ainda não participa deste teste. O gateway MCP presente no projeto usa um
cliente simulado; portanto, não é necessário transformar o Mac em servidor MCP.

## Serviços e acessos necessários

| Componente | Precisa estar ativo? | Função |
|---|---:|---|
| Docker Desktop | Sim | Executa os containers locais. |
| PostgreSQL/pgvector | Sim | Persiste execuções, evidências e auditoria. É iniciado pelo Compose. |
| API do Orquestrador | Sim | Coordena a coleta e os agentes e publica a interface. É iniciada pelo Compose. |
| Interface web | Sim, para o teste visual | É servida pela própria API em `/ui/`; não é um container separado. |
| GitHub | Sim | Fornece as evidências do repositório público via HTTPS. |
| Provedor LLM externo | Não | O teste usa `AIEO_LLM_PROVIDER=simulated`. |
| Token GitHub | Não | `app-financas` é público. |
| Servidor MCP | Não | O transporte MCP real ainda não está implementado. |
| Prometheus, Grafana e Alertmanager | Não | São úteis para o laboratório de observabilidade, mas não para esta validação. |

## 1. Fluxo completo após ligar o Mac

Esta é a sequência principal para começar do zero depois de ligar o equipamento.

### 1.1. Iniciar o Docker Desktop

Abra **Aplicativos > Docker** ou execute:

```bash
open -a Docker
```

Aguarde o Docker Engine responder. Este comando espera por até dois minutos:

```bash
for tentativa in $(seq 1 60); do
  if docker info >/dev/null 2>&1; then
    echo "Docker está pronto."
    break
  fi
  if [ "$tentativa" = "60" ]; then
    echo "Docker não iniciou no prazo esperado." >&2
    exit 1
  fi
  sleep 2
done
```

Não execute `docker compose up` antes de `docker info` responder sem erro.

### 1.2. Obter ou abrir o Orquestrador

Se o repositório **já existe neste Mac**:

```bash
cd /Users/ariroberto/Documents/ai-engineering-orchestrator
git switch main
git pull --ff-only origin main
git status --short --branch
```

Resultado esperado: a branch é `main`, está sincronizada com `origin/main` e não existem alterações
locais inesperadas. Não continue com `git pull` se houver arquivos seus ainda não salvos no Git.

Se estiver preparando **outro computador**, clone primeiro:

```bash
mkdir -p "$HOME/Documents"
cd "$HOME/Documents"
git clone https://github.com/AriRoberto/ai-engineering-orchestrator.git
cd ai-engineering-orchestrator
git switch main
```

Todos os comandos seguintes devem ser executados dentro da pasta
`ai-engineering-orchestrator`, e não dentro do repositório `app-financas`.

## 2. Confirmar os pré-requisitos

Abra o Docker Desktop e aguarde o mecanismo ficar disponível. Depois execute:

```bash
docker version
docker compose version
docker info --format 'Docker {{.ServerVersion}} | CPUs={{.NCPU}} | memória={{.MemTotal}}'
curl --version
python3 --version
make --version
```

Todos os comandos devem terminar sem erro. Confirme também que o GitHub está acessível:

```bash
curl --fail --silent --show-error \
  https://api.github.com/repos/AriRoberto/app-financas \
  | python3 -m json.tool \
  | head -40
```

O JSON deve conter, entre outros campos, `"full_name": "AriRoberto/app-financas"` e
`"private": false`.

## 3. Conferir a configuração local

Se o arquivo `.env` ainda não existir, crie-o a partir do exemplo:

```bash
test -f .env || cp .env.example .env
```

Esse comando preserva um `.env` já existente. Não use `cp .env.example .env` sem a verificação,
pois isso substituiria configurações locais.

O arquivo `.env` deve manter o laboratório em desenvolvimento, sem autenticação local obrigatória
e sem provedor LLM pago. Confira estas propriedades no editor:

```dotenv
AIEO_ENVIRONMENT=development
AIEO_API_AUTH_ENABLED=false
AIEO_DEMO_MODE=true
AIEO_LLM_PROVIDER=simulated
AIEO_DATABASE_URL=postgresql+psycopg://aieo:aieo@postgres:5432/aieo
```

Não é necessário colocar token GitHub, chave OpenAI ou URL de MCP no `.env`. Não publique esse
arquivo nem mostre seu conteúdo completo em logs ou capturas de tela.

O cadastro confiável do piloto já existe em `configs/projects/app-financas.yaml` e aponta para:

```text
https://github.com/AriRoberto/app-financas
```

## 4. Subir os containers

Execute:

```bash
docker compose up --build -d
```

Esse comando baixa as imagens necessárias, constrói o Orquestrador, cria a rede local, inicia o
PostgreSQL/pgvector, espera o banco ficar saudável e inicia a API com a interface web.

Na primeira execução, o download e o build podem levar alguns minutos. Nas inicializações futuras,
quando o código e as dependências não tiverem mudado, você pode usar apenas:

```bash
docker compose up -d
```

Confirme o estado:

```bash
docker compose ps
```

Devem aparecer os serviços `postgres` e `api`. O banco deve estar saudável e a API deve estar
ativa na porta `8000`.

Aguarde a API ficar pronta:

```bash
for tentativa in $(seq 1 30); do
  if curl --fail --silent http://localhost:8000/ready >/dev/null; then
    echo "Orquestrador está pronto."
    break
  fi
  if [ "$tentativa" = "30" ]; then
    echo "Orquestrador não ficou pronto. Consulte os logs." >&2
    docker compose logs --tail=200 api postgres
    exit 1
  fi
  sleep 2
done
```

Neste ponto, os serviços necessários para analisar o `app-financas` estão ativos.

## 5. Executar a validação automatizada recomendada

Na raiz do Orquestrador:

```bash
make lab-fase4
```

O script também executa `docker compose up --build -d`. Portanto, é possível usar
`make lab-fase4` diretamente depois que o Docker estiver pronto. O passo anterior foi apresentado
separadamente para deixar explícito quais containers são iniciados e facilitar o diagnóstico.

O laboratório realiza quatro verificações:

1. inicia PostgreSQL e API;
2. consulta o `app-financas` e executa os especialistas;
3. confirma que revisão, fontes e auditoria foram persistidas;
4. confirma que o projeto privado `app-ams` é recusado sem credencial.

Resultado final esperado:

```text
✓ Laboratório da Fase 4 concluído com sucesso.
Execução: <UUID>
Encerrar: make compose-down
```

Guarde o UUID apresentado. Ele identifica a execução persistida.

### Comando de demonstração

Para preparar os serviços, executar a análise e deixar a UI pronta em um único comando:

```bash
make demo
```

Esse comando usa `AriRoberto/app-financas` por padrão, valida a versão da API e a existência da UI,
confirma revisão Git e modo somente leitura e imprime o ID da execução. Abra a seção
**Relatório técnico** para ver os achados por especialista, proveniência e fontes, copiar o relatório
em Markdown ou imprimi-lo em PDF.

Atalho direto para o relatório da execução mais recente do projeto selecionado:

```text
http://localhost:8000/ui/?section=report
```

Para demonstrar outro repositório público do GitHub sem editar YAML manualmente:

```bash
make demo REPOSITORY=OWNER/REPOSITORY
```

Exemplo com ID, branch e pedido explícitos:

```bash
./scripts/demo-projeto.sh \
  --repository OWNER/REPOSITORY \
  --project-id projeto-demo \
  --branch main \
  --prompt "Revise arquitetura, segurança, testes e riscos operacionais" \
  --open-browser
```

O repositório precisa ser público. A configuração temporária fica em `.aieo-demo/`, ignorada pelo
Git, e continua impondo `read-only`. O script não executa nem modifica o projeto analisado.

## 6. Confirmar os serviços ativos

```bash
docker compose ps
```

Devem aparecer:

- `postgres`, saudável;
- `api`, ativa e publicada na porta `8000`.

Valide os endpoints:

```bash
curl --fail --silent --show-error http://localhost:8000/health \
  | python3 -m json.tool

curl --fail --silent --show-error http://localhost:8000/ready \
  | python3 -m json.tool
```

`/health` confirma que o processo está vivo. `/ready` confirma que a API está pronta, incluindo sua
dependência do PostgreSQL.

## 7. Fazer uma análise pela interface

Abra no navegador:

```text
http://localhost:8000/ui/
```

Na interface:

1. selecione `app-financas`;
2. escreva o pedido:

   ```text
   Revise arquitetura, banco de dados, qualidade, segurança, documentação e operação. Cite as evidências utilizadas e priorize os riscos encontrados.
   ```

3. marque **Incluir conteúdo permitido dos arquivos**;
4. deixe a seleção de agentes vazia para testar o roteamento automático, ou selecione os agentes
   desejados;
5. clique em **Executar análise**;
6. aguarde o estado `COMPLETED`;
7. confira agentes participantes, resultado consolidado e fontes de evidência.

O resultado é uma análise controlada dos arquivos coletados. Como o provedor é simulado, esta etapa
valida a orquestração e a rastreabilidade, não a qualidade de um modelo externo pago.

## 8. Fazer a mesma análise pelo terminal

```bash
curl --fail --silent --show-error \
  -X POST http://localhost:8000/v1/evidence/executions \
  -H 'Content-Type: application/json' \
  -d '{
    "project_id": "app-financas",
    "prompt": "Revise arquitetura, banco de dados, qualidade, segurança, documentação e operação. Cite as evidências utilizadas e priorize os riscos encontrados.",
    "demo": true,
    "include_content": true,
    "preferred_agents": []
  }' \
  | tee /tmp/aieo-app-financas-execucao.json \
  | python3 -m json.tool
```

Na resposta, confirme:

- `status` igual a `COMPLETED`;
- `request.project_id` igual a `app-financas`;
- provedor de evidência igual a `github`;
- `read_only` igual a `true`;
- `revision` com o SHA Git consultado;
- lista de agentes utilizada;
- `evidence_sources` com URLs do GitHub;
- nenhuma credencial ou segredo no resultado.

Extraia o ID da resposta:

```bash
execution_id="$(python3 -c \
  'import json; print(json.load(open("/tmp/aieo-app-financas-execucao.json"))["id"])')"
printf '%s\n' "$execution_id"
```

Consulte a execução persistida:

```bash
curl --fail --silent --show-error \
  "http://localhost:8000/v1/executions/${execution_id}?project_id=app-financas" \
  | python3 -m json.tool
```

Consulte a auditoria de acesso às evidências:

```bash
curl --fail --silent --show-error \
  'http://localhost:8000/v1/evidence/audits?project_id=app-financas' \
  | python3 -m json.tool
```

O registro mais recente deve indicar `COMPLETED`, `visibility` pública e acesso não autenticado.

## 9. Critérios objetivos de aprovação

Considere esta validação aprovada somente se todos os itens abaixo forem verdadeiros:

- `make lab-fase4` termina com sucesso;
- `api` e `postgres` permanecem ativos;
- `/health` e `/ready` respondem sem erro;
- a execução do `app-financas` termina em `COMPLETED`;
- a resposta contém uma revisão Git de 40 caracteres;
- as fontes apontam para o repositório `AriRoberto/app-financas`;
- o acesso aparece como público, não autenticado e somente leitura;
- a execução pode ser recuperada pelo ID;
- a auditoria correspondente foi persistida;
- nenhuma alteração, branch ou Pull Request é criado no `app-financas`.

Essa aprovação demonstra coleta real, governança, orquestração, persistência e rastreabilidade. Ela
não demonstra execução funcional do código do `app-financas`, MCP real nem análise por LLM externo.

## 10. Diagnóstico de problemas

### Docker não responde

Abra o Docker Desktop e aguarde até ficar operacional:

```bash
docker info
```

### Porta 8000 ocupada

```bash
lsof -nP -iTCP:8000 -sTCP:LISTEN
```

Encerre conscientemente o processo conflitante ou o Compose antigo antes de repetir o laboratório.

### API ou banco não ficam prontos

```bash
docker compose ps
docker compose logs --tail=200 api postgres
```

### Falha ao consultar o GitHub

```bash
curl --fail --silent --show-error \
  https://api.github.com/repos/AriRoberto/app-financas \
  | python3 -m json.tool
```

Se esse comando falhar, verifique internet, DNS, proxy, VPN e limites temporários da API pública do
GitHub. O piloto público não deve solicitar token como primeira solução.

### Resposta HTTP 401

Confirme no `.env`:

```dotenv
AIEO_API_AUTH_ENABLED=false
```

Depois recrie a API:

```bash
docker compose up --build -d --force-recreate api
```

### Recomeçar com dados vazios

O comando abaixo remove também o volume PostgreSQL e todo o histórico local. Use-o somente se não
precisar preservar execuções anteriores:

```bash
docker compose down --volumes
docker compose up --build -d
```

## 11. Encerrar o ambiente

Para parar os containers e preservar os dados:

```bash
make compose-down
```

Confirme:

```bash
docker compose ps
```

Nenhum serviço do projeto deve permanecer em execução. O volume do PostgreSQL continua disponível
para a próxima inicialização.

## 12. Sequência resumida para os próximos dias

Depois da primeira preparação, esta é a rotina após ligar o Mac:

```bash
open -a Docker
cd /Users/ariroberto/Documents/ai-engineering-orchestrator
docker info
git switch main
git pull --ff-only origin main
docker compose up -d
curl --fail --silent http://localhost:8000/ready | python3 -m json.tool
```

Abra <http://localhost:8000/ui/>, selecione `app-financas` e execute a análise. Para repetir toda a
validação automatizada:

```bash
make lab-fase4
```

Para uma apresentação completa com relatório técnico, prefira:

```bash
make demo
```

Ao terminar:

```bash
make compose-down
```
