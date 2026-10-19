# Laboratório prático — piloto privado da Fase 4

Este laboratório valida a leitura somente de metadados do repositório privado `AriRoberto/app-ams`.
O coletor não escreve no GitHub e não solicita conteúdo de arquivos. O token nunca deve ser
colocado no repositório, na imagem Docker ou na solicitação da API.

## Pré-requisitos

- Docker Compose v2 e acesso HTTPS a `api.github.com`;
- um token GitHub de escopo mínimo, limitado ao repositório `app-ams` e com permissão de conteúdo
  somente leitura;
- um arquivo local contendo apenas o token, sem prefixo `Bearer`.

Crie o arquivo fora do repositório e restrinja a leitura ao usuário local:

```bash
mkdir -p "$HOME/.config/aieo"
umask 077
printf 'Token somente leitura do GitHub: ' >&2
IFS= read -r -s token
printf '\n' >&2
printf '%s' "$token" > "$HOME/.config/aieo/github-app-ams-token"
unset token
chmod 600 "$HOME/.config/aieo/github-app-ams-token"
export AIEO_GITHUB_PRIVATE_READ_TOKEN_FILE="$HOME/.config/aieo/github-app-ams-token"
```

Não use `set -x` nesse terminal. O Compose monta o arquivo como secret somente leitura no container;
a aplicação continua executando como usuário não-root.

## Execução

```bash
make lab-fase4-privado
```

O laboratório inicia a API, confirma sua saúde e solicita uma execução com `include_content=false`.
Ele valida que:

- a execução completou e identifica `app-ams` como privado;
- a evidência marca acesso autenticado e somente leitura;
- uma revisão Git identificável e metadados de arquivos foram retornados;
- todos os arquivos permanecem em estado `metadata-only`;
- a tentativa concluída foi persistida na auditoria e vinculada à execução;
- a resposta não contém nomes de cabeçalho ou marcadores associados à credencial.

Ao terminar, o script para o container da API automaticamente para desmontar o secret. O PostgreSQL
pode continuar ativo; para encerrar todo o ambiente, execute:

```bash
make compose-down
```

O valor também pode ser fornecido por `AIEO_GITHUB_PRIVATE_READ_TOKEN` no ambiente local, mas o
arquivo secreto é preferível em Compose. `AIEO_GITHUB_PRIVATE_READ_REPOSITORY` limita o provedor a
`AriRoberto/app-ams`; alterar a URL do projeto ou a solicitação HTTP não amplia esse escopo.
Credencial ausente resulta em HTTP 403; erros de acesso ao GitHub não usam dados parciais.

O laboratório requer uma credencial válida e acesso real ao projeto. Testes automatizados com
transporte simulado não substituem essa validação; não registre o token, a resposta de autenticação
ou conteúdo privado em logs, issues ou relatórios.
