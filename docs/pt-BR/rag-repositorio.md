# RAG: ingestão local de repositórios

Esta primeira etapa publica arquivos de uma revisão Git na base de conhecimento
existente. A busca e a consolidação do orquestrador passam a encontrar esses trechos.
Os embeddings continuam sendo os de demonstração, com 16 dimensões. Embeddings
semânticos e busca SQL são etapas posteriores.

## Comportamento

- A prévia é o padrão: não abre conexão com o banco e não publica documentos.
- Somente arquivos do commit informado são lidos. Alterações locais e arquivos
  não versionados não entram no índice; o relatório sinaliza alterações rastreadas.
- O scanner usa objetos Git, não segue links simbólicos e não percorre submódulos.
- Código, Markdown e configurações textuais têm uma lista de extensões permitidas.
  Credenciais, `.env`, dependências, builds, lockfiles e `evals/` são excluídos.
  Exemplos adversariais detectados pelo guard ficam em quarentena, inclusive em testes.
- Segredos reconhecidos são sanitizados por linha, preservando a numeração.
  Essa proteção por padrões não é garantia de detecção de todos os segredos:
  revise os arquivos aceitos antes de publicar uma coleção sensível.
- Os fragmentos preservam indentação e linhas, com limite padrão de 1600 caracteres.
  Linhas maiores são divididas; ainda não há fragmentação por AST nem sobreposição.
- Cada documento guarda caminho, revisão, hash do conteúdo sanitizado, tipo,
  redactions e identificação do embedding e fragmentador. Resultados de busca
  incluem proveniência e linhas dos trechos.
- Repetir a mesma indexação mantém IDs e data de criação. Em outra revisão,
  documentos inalterados mantêm IDs e atualizam a revisão de origem.
- A publicação substitui atomicamente apenas a coleção do projeto escolhido.
  Documentos manuais e outras coleções/projetos são preservados. Um lock transacional
  serializa publicações concorrentes da mesma coleção no PostgreSQL.
- Arquivos removidos, excluídos pela política ou colocados em quarentena saem da
  coleção ativa numa publicação bem-sucedida. Limite total excedido ou falha de
  leitura/escrita aborta a publicação. Coleção vazia exige `--allow-empty`.

Use uma coleção diferente para cada repositório de um mesmo projeto. Não reutilize
a mesma coleção para raízes diferentes, pois isso substituiria os documentos anteriores.
O CLI acessa o banco diretamente: é uma ferramenta administrativa, executada com
credencial de banco autorizada, e não usa a autenticação HTTP da aplicação.

## Preparação local

Requer Python 3.12+, Git e as dependências do projeto:

```bash
python -m pip install -e '.[dev]'
```

O banco precisa da migração `005_repository_knowledge.sql`. Bancos novos do Compose
recebem a migração automaticamente. Em um volume existente da demo, reconstruir a
imagem e aplicar migrações antes de recriar a API:

```bash
docker compose -p aieo-demo -f compose.yaml -f compose.demo.yaml build api
docker compose -p aieo-demo -f compose.yaml -f compose.demo.yaml run --rm --no-deps api \
  python -m ai_engineering.infrastructure.migrations
docker compose -p aieo-demo -f compose.yaml -f compose.demo.yaml up -d --no-deps api
```

Esses comandos são para a demo simulada já preparada. Se estiver usando OpenAI ou
acesso privado, mantenha também seus arquivos Compose e variáveis de inicialização.
Não remova volumes. A migração é aditiva e pode ser reaplicada.

## Prévia

Na raiz do repositório:

```bash
python -m ai_engineering.knowledge.repository_ingestion \
  --project-id ai-engineering-orchestrator --root .
```

O JSON contém revisão, estado da cópia local, contagens e situação de cada arquivo,
sem imprimir os trechos. Use `--revision <commit-ou-tag>` para fixar uma revisão.
Nenhum arquivo é enviado a um serviço externo.

## Publicação

Defina `AIEO_DATABASE_URL` no ambiente ou no `.env`, apontando para o banco desejado,
e execute o mesmo comando com `--apply`. A credencial não é argumento de linha de
comando e não é impressa no relatório. O host `postgres` do Compose só é resolvido
na rede Docker: para usar um Python no host, o banco deve estar acessível por uma
conexão configurada para esse host.

```bash
python -m ai_engineering.knowledge.repository_ingestion \
  --project-id ai-engineering-orchestrator --root . --apply
```

O resultado inclui `added`, `removed` e `unchanged`. Uma alteração de conteúdo conta
como remoção da versão anterior e adição da nova. Revise a prévia antes de aplicar
mudanças de limites, pois arquivos que deixam de ser elegíveis saem da coleção.

A imagem normal da API não inclui Git. Para indexar dentro da rede da demo sem
instalar Python/Git no host, use um container administrativo descartável:

```bash
docker compose -p aieo-demo -f compose.yaml -f compose.demo.yaml run --rm --no-deps \
  --user root -v "$PWD:/repository:ro" api sh -c \
  'apt-get update -qq && apt-get install -y -qq git && git config --global --add safe.directory /repository && python -m ai_engineering.knowledge.repository_ingestion --root /repository --project-id ai-engineering-orchestrator'
```

Esse comando instala Git somente no container descartável e lê o checkout em modo
somente leitura. Após revisar a prévia, repita adicionando `--apply` ao final do
comando Python, dentro das aspas. Não execute com `--allow-empty` a menos que queira
autorizar explicitamente uma coleção vazia.

## Consulta

```bash
curl --fail-with-body http://localhost:8000/v1/knowledge/search \
  -H 'Content-Type: application/json' \
  -d '{"project_id":"ai-engineering-orchestrator","query":"Como funciona o isolamento de conhecimento?","limit":5,"include_shared":false}'
```

Em ambientes autenticados, inclua sua credencial HTTP e autorização de projeto.
A ingestão não cadastra o projeto no catálogo visual. A API de conhecimento permite
consultar esse namespace; para selecioná-lo na UI, cadastre também o projeto pelo
fluxo de catálogo existente.

## Validação e próximos passos

```bash
python -m pytest tests/unit/test_repository_ingestion.py tests/unit/test_knowledge.py
```

O teste `tests/integration/test_repository_knowledge.py` exige
`AIEO_TEST_DATABASE_URL` apontando para PostgreSQL descartável com pgvector. Ele
aplica migrações, verifica rollback e isolamento e remove seus documentos ao final.
Sem essa variável, o teste é ignorado.

Próximas etapas: provedor semântico e migração dos vetores; recuperação híbrida em
SQL; seleção de contexto por orçamento; citações verificadas; sincronização GitHub.
