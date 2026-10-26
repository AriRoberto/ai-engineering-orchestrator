# Guia do usuário — Orquestrador e Agentes de IA

Este guia ensina a instalar e usar o **AI Engineering Orchestrator** em um computador local. O caminho principal usa Docker e pode ser seguido por uma pessoa sem experiência com programação.

> **Situação atual da solução:** a versão `0.2.0` coleta evidências de repositórios GitHub em modo somente leitura, escolhe especialistas, executa análises e registra resultados e auditoria. Ela **ainda não altera arquivos, cria branches, faz commits, push ou Pull Requests reais automaticamente**. Esses itens são explicados como fluxo manual seguro na seção [Branches, commits e Pull Requests](#7-branches-commits-e-pull-requests).

## 1. Visão geral

O Orquestrador recebe uma solicitação, identifica quais especialistas são adequados, limita a quantidade de trabalho, executa os agentes e reúne os resultados em uma única execução auditável.

O fluxo atual é:

1. você cadastra um projeto por meio de um arquivo YAML confiável;
2. a solução consulta o GitHub sem modificar o repositório;
3. o Orquestrador interpreta o pedido e seleciona os agentes;
4. cada agente examina as evidências relacionadas à sua especialidade;
5. a execução, as fontes consultadas e os eventos de auditoria são armazenados no PostgreSQL;
6. você consulta o resultado pela interface, pelo Swagger ou pela API.

### Agentes disponíveis

| Agente | Função na implementação atual |
|---|---|
| `software-engineer` | Identifica a tecnologia do projeto por arquivos como `pyproject.toml`, `package.json` e outros manifestos. |
| `devops` | Verifica indícios de contêineres e integração contínua, como `Dockerfile` e `.github/workflows/`. |
| `kubernetes` | Localiza manifestos e estruturas relacionadas a Kubernetes e Helm. |
| `linux-sre` | Produz diagnóstico a partir das evidências recebidas; não executa comandos no computador analisado. |
| `database` | Identifica SQL, schemas e migrações de banco de dados. |
| `qa` | Localiza testes e evidências de validação em CI. |
| `security` | Procura controles e nomes de arquivos sensíveis e aplica regras de redação ou quarentena. |
| `documentation` | Avalia arquivos Markdown e documentos essenciais, como `README.md`, `CHANGELOG.md` e `SECURITY.md`. |

Os agentes trabalham de forma determinística e controlada. O provedor de IA padrão é **simulado**, portanto não é necessário cadastrar uma chave de modelo para executar os laboratórios locais.

## 2. Antes de começar

### Requisitos

Instale no computador:

- Git;
- Docker Desktop, com Docker Engine 24 ou posterior e Docker Compose v2;
- `curl`, normalmente já disponível no macOS e no Linux;
- Python 3, usado apenas pelos scripts de validação dos laboratórios.

Confirme no **Terminal**:

```bash
git --version
docker --version
docker compose version
curl --version
python3 --version
```

**Resultado esperado:** cada comando mostra um número de versão. Abra o Docker Desktop e aguarde até ele informar que o mecanismo está em execução.

### Obter o projeto

No Terminal, escolha uma pasta de trabalho e execute:

```bash
git clone https://github.com/AriRoberto/ai-engineering-orchestrator.git
cd ai-engineering-orchestrator
git switch main
```

Se o repositório já estiver no computador, entre na pasta e atualize-o:

```bash
cd ai-engineering-orchestrator
git switch main
git pull --ff-only origin main
```

**Resultado esperado:** o Terminal informa que a branch `main` está atualizada.

## 3. Instalação e primeira inicialização

Execute os comandos abaixo na raiz do repositório `ai-engineering-orchestrator`:

```bash
cp .env.example .env
docker compose up --build -d
docker compose ps
```

O primeiro início pode demorar alguns minutos porque o Docker precisa construir e baixar imagens. O arquivo `.env` criado usa, por padrão, autenticação local desabilitada, dados de demonstração habilitados e provedor de IA simulado.

**Resultado esperado:** os serviços `api` e `postgres` aparecem como iniciados ou saudáveis.

Teste a API:

```bash
curl --fail --silent http://localhost:8000/health
```

**Resultado esperado:** uma resposta JSON indicando que o serviço está saudável.

Abra no navegador:

- interface: <http://localhost:8000/ui/>;
- documentação interativa da API: <http://localhost:8000/docs>;
- prontidão da aplicação: <http://localhost:8000/ready>.

Para encerrar sem apagar os arquivos do projeto:

```bash
make compose-down
```

Para iniciar novamente:

```bash
docker compose up -d
```

## 4. Configurar acesso ao GitHub

### Projeto público

Um repositório público pode ser consultado sem token. O laboratório de `app-financas` usa esse modo.

### Projeto privado: criar um token mínimo

Para um repositório privado, crie um **fine-grained personal access token** exclusivo e temporário:

1. entre no GitHub;
2. clique em sua foto, no canto superior direito;
3. acesse **Settings**;
4. no menu esquerdo, abra **Developer settings**;
5. abra **Personal access tokens** e depois **Fine-grained tokens**;
6. escolha **Generate new token**;
7. informe um nome, por exemplo `aieo-app-ams-local-test`;
8. selecione uma expiração curta;
9. em **Resource owner**, selecione o proprietário do repositório;
10. em **Repository access**, escolha **Only select repositories** e selecione somente `app-ams`;
11. em **Permissions**, clique em **Add permissions**, escolha **Repository permissions** e defina **Contents: Read-only**;
12. não conceda permissões de conta e não conceda escrita;
13. gere o token e copie-o uma única vez.

O GitHub também mostra acesso de leitura a metadados. Isso é normal e acompanha o acesso ao conteúdo do repositório.

> **Cuidado:** nunca cole o token em um arquivo do repositório, em uma conversa, em uma captura de tela, no histórico do shell ou no campo de chave da interface do Orquestrador. A chave mostrada na interface é uma chave da API local, não um token GitHub.

### Armazenar sem expor a credencial

No macOS ou Linux, execute no Terminal:

```bash
mkdir -p "$HOME/.config/aieo"
umask 077
printf 'Cole o token GitHub e pressione Enter: ' >&2
IFS= read -r -s token
printf '\n' >&2
printf '%s' "$token" > "$HOME/.config/aieo/github-app-ams-token"
unset token
chmod 600 "$HOME/.config/aieo/github-app-ams-token"
```

Esse procedimento não exibe o token e o armazena fora do repositório. Confira apenas a permissão, sem mostrar o conteúdo:

```bash
ls -l "$HOME/.config/aieo/github-app-ams-token"
```

**Resultado esperado:** somente o proprietário possui permissão de leitura e escrita (`-rw-------`).

### Testar a conexão privada

Na raiz de `ai-engineering-orchestrator`, execute:

```bash
AIEO_GITHUB_PRIVATE_READ_TOKEN_FILE="$HOME/.config/aieo/github-app-ams-token" make lab-fase4-privado
```

**Resultado esperado:** ao final aparece `Laboratório privado da Fase 4 concluído com sucesso`. O teste consulta somente metadados de `app-ams`, confirma a auditoria e para automaticamente a API privada para desmontar o secret. O token não é incluído no resultado da execução.

Depois do teste, encerre os demais serviços:

```bash
make compose-down
```

Quando não precisar mais da credencial, revogue-a em **GitHub > Settings > Developer settings > Personal access tokens > Fine-grained tokens**. Também apague o arquivo local com uma ferramenta segura de sua preferência.

## 5. Adicionar um projeto

Projetos autorizados ficam em `configs/projects/`. A API não aceita uma URL arbitrária enviada pelo usuário; ela procura um arquivo de configuração previamente revisado. Isso reduz o risco de acesso a um repositório indevido.

### 5.1 Escolher o identificador

Use letras minúsculas, números e hífens, por exemplo `meu-projeto`. O nome do arquivo e o campo `id` devem ser iguais:

```text
configs/projects/meu-projeto.yaml
id: meu-projeto
```

### 5.2 Criar a configuração

Na raiz do Orquestrador, crie `configs/projects/meu-projeto.yaml` com um editor de texto:

```yaml
id: meu-projeto
owner: SEU-USUARIO-OU-ORGANIZACAO
repository: https://github.com/SEU-USUARIO-OU-ORGANIZACAO/SEU-REPOSITORIO
default_branch: main
visibility: public
mode: read-only
knowledge_namespace: project/meu-projeto
mcp:
  allowed_tools:
    - project-catalog:project_summary
```

Para um repositório privado, altere somente a visibilidade:

```yaml
visibility: private
```

Mantenha `mode: read-only`. Não adicione token, senha ou chave ao YAML.

### 5.3 Reiniciar e verificar

Como a configuração é copiada para a imagem da API, reconstrua o serviço:

```bash
docker compose up --build -d
curl --fail --silent http://localhost:8000/ready
```

**Resultado esperado:** a API retorna uma resposta de prontidão. O projeto estará autorizado para coleta quando `id`, nome do arquivo, URL, proprietário e visibilidade forem consistentes.

> Cadastrar um projeto pela interface web ainda é uma funcionalidade **pendente**. Hoje o cadastro é feito por arquivo YAML e exige acesso aos arquivos do Orquestrador.

## 6. Solicitar e acompanhar uma análise

### Opção mais simples: interface web

1. abra <http://localhost:8000/ui/>;
2. escolha o projeto autorizado na lista;
3. descreva a análise desejada;
4. opcionalmente, selecione agentes específicos — sem seleção, o roteamento é automático;
5. marque **Incluir conteúdo permitido dos arquivos** somente quando a análise precisar do texto dos arquivos;
6. clique em **Executar análise**.

**Resultado esperado:** a execução aparece no histórico com estado `COMPLETED`, os agentes usados e o resultado consolidado. Projetos privados continuam exigindo que a API tenha sido iniciada com a credencial de leitura apropriada.

### Opção pelo Swagger

1. abra <http://localhost:8000/docs>;
2. localize `POST /v1/evidence/executions`;
3. clique em **Try it out**;
4. informe o projeto e o pedido, conforme o exemplo abaixo;
5. clique em **Execute**.

Exemplo para um repositório público:

```json
{
  "project_id": "app-financas",
  "prompt": "Revise arquitetura, banco de dados, QA, segurança e documentação",
  "demo": true,
  "include_content": true,
  "preferred_agents": ["software-engineer", "database", "qa", "security", "documentation"]
}
```

**Resultado esperado:** código HTTP `201`, estado `COMPLETED`, um campo `id`, a lista de agentes participantes e as fontes de evidência. Omita `preferred_agents` ou envie uma lista vazia para o Orquestrador selecionar os agentes a partir do pedido.

### Opção pelo Terminal

```bash
curl --fail --silent --show-error \
  -X POST http://localhost:8000/v1/evidence/executions \
  -H 'Content-Type: application/json' \
  -d '{
    "project_id": "app-financas",
    "prompt": "Revise arquitetura, banco de dados, QA, segurança e documentação",
    "demo": true,
    "include_content": true,
    "preferred_agents": []
  }' | python3 -m json.tool
```

Para analisar um projeto privado, a API precisa ter sido iniciada com o arquivo de token montado, como faz `make lab-fase4-privado`. Para o primeiro uso, prefira esse laboratório pronto em vez de manipular o secret manualmente.

### Consultar uma execução

Copie o valor de `id` retornado e execute:

```bash
EXECUTION_ID='COLE-O-ID-AQUI'
curl --fail --silent \
  "http://localhost:8000/v1/executions/$EXECUTION_ID?project_id=app-financas" \
  | python3 -m json.tool
```

Para listar o histórico do projeto:

```bash
curl --fail --silent \
  'http://localhost:8000/v1/executions?project_id=app-financas' \
  | python3 -m json.tool
```

Os estados possíveis são `PENDING`, `PLANNING`, `RUNNING`, `WAITING_APPROVAL`, `COMPLETED`, `FAILED` e `CANCELLED`. A execução local atual é síncrona: normalmente a resposta chega já concluída. Acompanhamento ao vivo por streaming ainda não existe.

## 7. Branches, commits e Pull Requests

A política implementada protege `main`, `master` e `develop`, proíbe force-push e merge automático e reserva branches no padrão:

```text
agents/<agente>/<tipo>-<descricao>-<identificador>
```

Exemplo válido:

```text
agents/documentation/docs-atualizar-guia-001
```

Toda operação de escrita deve passar por aprovação humana. Porém, nesta versão, o Orquestrador **somente valida essa política**. A criação da branch, a edição dos arquivos, o commit, o push e o Pull Request automatizados ainda estão pendentes.

Quando uma análise indicar uma alteração, faça o fluxo manual abaixo no repositório analisado:

```bash
git switch develop
git pull --ff-only origin develop
git switch -c agents/documentation/docs-atualizar-guia-001

# Edite os arquivos recomendados e execute os testes do projeto.

git status --short
git add CAMINHO-DO-ARQUIVO
git commit -m "docs: atualizar guia"
git push -u origin agents/documentation/docs-atualizar-guia-001
```

No GitHub:

1. abra o repositório;
2. clique em **Compare & pull request**;
3. selecione `develop` como branch de destino, ou a branch definida pela política do projeto;
4. marque **Create draft pull request** enquanto o trabalho estiver em revisão;
5. aguarde o CI e a aprovação humana;
6. faça o merge pela interface;
7. escolha **Delete branch** depois do merge.

Não faça alterações diretamente em `main`. Se o projeto não tiver `develop`, confirme a política com o responsável antes de escolher a base.

## 8. Exemplo prático com os projetos piloto

### 8.1 `app-financas` — repositório público

Repositório: <https://github.com/AriRoberto/app-financas>

A configuração já existe em `configs/projects/app-financas.yaml`. Na raiz do Orquestrador, execute:

```bash
make lab-fase4
```

O laboratório:

1. inicia a aplicação;
2. coleta evidências públicas e conteúdo permitido;
3. executa especialistas de arquitetura, banco, QA, segurança e documentação;
4. confirma a proveniência e a auditoria;
5. confirma que acesso privado sem credencial é bloqueado.

**Resultado esperado:** `Laboratório da Fase 4 concluído com sucesso`, seguido do identificador da execução.

Abra <http://localhost:8000/ui/>, escolha `app-financas` na lista de projetos e clique em **Atualizar**.

### 8.2 `app-ams` — repositório privado

Repositório: <https://github.com/AriRoberto/app-ams>

A configuração já existe em `configs/projects/app-ams.yaml`. Depois de criar e armazenar o token de leitura conforme a seção 4, execute:

```bash
AIEO_GITHUB_PRIVATE_READ_TOKEN_FILE="$HOME/.config/aieo/github-app-ams-token" make lab-fase4-privado
```

Esse laboratório usa `include_content: false`: coleta nomes, tamanhos, hashes e revisão, mas não inclui o conteúdo dos arquivos. É o comportamento deliberadamente conservador do piloto privado.

**Resultado esperado:** o laboratório conclui, registra uma auditoria autenticada e informa que o secret não entrou na execução. A API privada é parada automaticamente ao final.

Para manter a API aberta e consultar `app-ams` pela interface seria necessário iniciar manualmente a sobreposição privada do Compose e manter o secret montado. Esse procedimento é operacional e não é recomendado como primeiro uso; o laboratório já comprova o fluxo privado com desmontagem automática do token.

## 9. Visualizar resultados

### Interface web

Abra <http://localhost:8000/ui/>. Escolha o projeto, por exemplo `app-financas`, e clique em **Atualizar**. A própria interface também inicia análises e permite usar o roteamento automático ou escolher agentes específicos. As páginas disponíveis mostram:

- **Execuções:** histórico e detalhes das análises;
- **Fontes:** evidências citadas;
- **Aprovações:** solicitações MCP pendentes, quando houver;
- **Auditoria:** registros de acesso às evidências.

No Compose padrão, a autenticação da API está desabilitada e o campo de chave pode ficar vazio. Se aparecer `Credencial de API ausente ou inválida`, confira se está usando exatamente `http://localhost:8000/ui/` e se o `.env` ainda contém a configuração padrão. A credencial GitHub nunca deve ser inserida nesse campo.

### Logs

Na raiz do Orquestrador:

```bash
docker compose logs -f api
```

Pressione `Ctrl+C` para parar de acompanhar os logs; isso não encerra a aplicação.

### Auditoria pela API

```bash
curl --fail --silent \
  'http://localhost:8000/v1/evidence/audits?project_id=app-financas' \
  | python3 -m json.tool
```

**Resultado esperado:** registros com situação, visibilidade, revisão consultada e identificador da execução.

### Alterações e Pull Requests

Os relatórios, as evidências, os eventos e os logs estão disponíveis. Uma lista de arquivos realmente alterados e links para Pull Requests criados pelos agentes **não estão disponíveis**, pois a versão atual não escreve no GitHub. Pull Requests feitos pelo fluxo manual devem ser consultados na aba **Pull requests** do repositório correspondente.

## 10. Problemas comuns

### `Cannot connect to the Docker daemon`

Abra o Docker Desktop, aguarde a inicialização e tente novamente:

```bash
docker compose up --build -d
```

### A interface, o Swagger ou `/ready` não abre

Verifique os contêineres e os logs:

```bash
docker compose ps
docker compose logs --tail=100 api
curl -v http://localhost:8000/health
```

Use a porta `8000` no Docker Compose. A porta `18080` pertence ao laboratório Kubernetes opcional e só funciona enquanto o `port-forward` estiver ativo.

### A porta `8000` já está ocupada

Descubra qual processo está usando a porta:

```bash
lsof -nP -iTCP:8000 -sTCP:LISTEN
```

Encerre o serviço conflitante ou altere conscientemente o mapeamento local no Compose. Não encerre processos desconhecidos sem confirmar sua finalidade.

### `Credencial de API ausente ou inválida`

No modo local padrão, recrie o `.env` a partir do exemplo e reinicie:

```bash
cp .env.example .env
docker compose up --build -d
```

Isso substitui ajustes locais no `.env`; faça uma cópia antes caso tenha configurações próprias. Não use o token GitHub como chave da API.

### `Projeto não configurado para coleta`

Confirme estes três itens:

```text
configs/projects/meu-projeto.yaml
id: meu-projeto
"project_id": "meu-projeto"
```

Depois reconstrua a API com `docker compose up --build -d`.

### Repositório privado retorna HTTP `403`

Confira se:

- o token não expirou nem foi revogado;
- o token foi limitado ao repositório correto;
- `Contents` está como `Read-only`;
- o arquivo possui permissão `600` ou `400`;
- a variável aponta para o arquivo correto.

Teste novamente:

```bash
chmod 600 "$HOME/.config/aieo/github-app-ams-token"
AIEO_GITHUB_PRIVATE_READ_TOKEN_FILE="$HOME/.config/aieo/github-app-ams-token" make lab-fase4-privado
```

### A interface mostra zero registros

Primeiro execute `make lab-fase4` ou crie uma análise no formulário da interface. Depois escolha o mesmo projeto e clique em **Atualizar**.

### O agente não criou branch ou Pull Request

Esse comportamento é esperado na versão `0.2.0`. A automação de escrita Git ainda não foi implementada. Use o fluxo manual da seção 7.

## 11. Checklist final

Marque cada item depois de confirmá-lo:

- [ ] Git, Docker, Docker Compose, `curl` e Python 3 estão instalados.
- [ ] O Docker Desktop está em execução.
- [ ] O arquivo `.env` foi criado a partir de `.env.example`.
- [ ] `docker compose ps` mostra API e PostgreSQL iniciados.
- [ ] `curl http://localhost:8000/health` retorna uma resposta saudável.
- [ ] A interface abre em <http://localhost:8000/ui/>.
- [ ] O Swagger abre em <http://localhost:8000/docs>.
- [ ] O projeto possui um YAML em `configs/projects/` com `mode: read-only`.
- [ ] `make lab-fase4` conclui a análise pública de `app-financas`.
- [ ] Para `app-ams`, o token é temporário, somente leitura e limitado ao repositório.
- [ ] O token está fora do repositório, com permissão `600` ou `400`.
- [ ] `make lab-fase4-privado` conclui sem expor a credencial.
- [ ] A interface ou a API mostra execuções, evidências e auditoria.
- [ ] Qualquer alteração real é feita em branch própria, revisada e integrada por uma pessoa.

## 12. Funcionalidades ainda pendentes

As seguintes capacidades não fazem parte da implementação atual e não devem ser pressupostas durante o uso:

- cadastrar ou editar projetos pela interface;
- acompanhar agentes em tempo real por streaming;
- editar arquivos do repositório automaticamente;
- criar branches, commits, push ou Pull Requests reais automaticamente;
- executar merge automático;
- usar transporte MCP real — o gateway atual é simulado;
- usar um modelo de IA real por padrão — o provedor padrão é simulado;
- operar como ambiente persistente de homologação ou produção com registry, Ingress/TLS, secret manager e identidade federada.

Para detalhes técnicos e decisões de arquitetura, consulte [README.md](../README.md), [Plano de implementação](pt-BR/plano-de-implementacao.md) e [Guia de arquitetura](pt-BR/guia-arquitetura.md).
