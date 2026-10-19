# Fase 4 — Primeiro piloto público somente leitura

Este incremento conecta o orquestrador ao repositório público `AriRoberto/app-financas`. Por padrão,
a coleta continua restrita aos metadados da árvore Git. O cliente pode solicitar, explicitamente, o
conteúdo textual de um subconjunto limitado com `include_content: true`.

## Fluxo implementado

1. o cliente solicita uma execução informando `project_id` e objetivo;
2. o backend carrega o repositório e a branch do YAML confiável do projeto;
3. a política exige `visibility: public` e `mode: read-only`;
4. a API do GitHub retorna a árvore e a revisão corrente;
5. o coletor filtra tipos relevantes e aplica limites;
6. caminhos, SHAs, tamanhos e URLs de origem entram no contexto da execução;
7. o orquestrador seleciona agentes e persiste o diagnóstico com a proveniência.

Endpoint:

```text
POST /v1/evidence/executions
```

Exemplo:

```json
{
  "project_id": "app-financas",
  "prompt": "Revise arquitetura, banco de dados, QA, segurança e documentação",
  "demo": true,
  "include_content": true
}
```

## Limites de coleta

| Controle | Padrão |
|---|---:|
| Arquivos aceitos | 200 |
| Tamanho por arquivo | 1 MB |
| Soma dos arquivos inventariados | 5 MB |
| Conteúdos baixados | 8 |
| Tamanho por conteúdo | 64 KB |
| Soma dos conteúdos | 256 KB |
| Timeout da chamada GitHub | 10 segundos |

Os limites são configurados por `AIEO_EVIDENCE_*`. Arquivos binários e extensões não relevantes
são ignorados. Diretórios gerados ou vendorizados, como `node_modules`, `.venv`, `dist`, `build`,
`target` e `vendor`, não consomem o orçamento. Caminhos absolutos, travessia `..`, SHAs inválidos e
tamanhos inconsistentes também são descartados. Uma resposta com `truncated=true` é recusada.

## Conteúdo textual controlado

Quando habilitada, a coleta prioriza README, manifestos, Dockerfile, SECURITY e CHANGELOG. Cada
conteúdo precisa ser UTF-8, recebe SHA-256 e passa por detecção de prompt injection e redaction de
segredos antes de ser persistido. O campo `content_status` registra o resultado:

- `included`: texto aprovado;
- `redacted`: texto aprovado após remoção de possíveis segredos;
- `quarantined`: indício de prompt injection; o texto não é exposto;
- `non-utf8`, `too-large` ou `total-limit`: conteúdo recusado pelo respectivo controle;
- `metadata-only`: conteúdo não solicitado ou não selecionado dentro do limite.

O conteúdo coletado não é executado. Os agentes recebem o contexto limitado, enquanto Segurança e
Documentação também usam os estados de controle para produzir diagnósticos rastreáveis.

## Contexto citado para análise

O terceiro incremento transforma somente conteúdos `included` ou `redacted` em um contexto limitado
por `AIEO_EVIDENCE_CONTEXT_MAX_CHARS`. Cada trecho preserva caminho, URL, SHA-256, indicação de
truncamento e uma citação `[evidence:<path>]`. As URLs usadas ficam registradas em
`execution.evidence_sources`.

Quando a consolidação LLM está habilitada, esse contexto entra em uma seção identificada como dado
externo não confiável. A instrução de sistema proíbe seguir comandos encontrados na evidência. Esse
controle complementa a quarentena, mas não substitui avaliações adversariais.

## Segurança e honestidade do resultado

O `project_id` não controla a URL remota. O destino vem dos YAMLs locais dos projetos e o transporte
usa somente `https://api.github.com`. O projeto público `app-financas` não exige credencial. O
piloto privado `app-ams` só pode ser lido com credencial autorizada para esse repositório; sem ela,
a API retorna HTTP 403. O token não integra o contexto da execução. Veja o
[laboratório privado](laboratorio-fase4-privado.md) para configuração e validação.

Os achados indicam padrões derivados do inventário e dos estados de conteúdo, não uma revisão
semântica completa do código. O modo `demo` continua recomendado até que exista análise controlada
e rastreável do texto aprovado.

## Evidência de validação

Em 15/10/2026, a consulta real da branch `main` retornou a revisão
`9ed4c91ed1e29c0ccfe7d69f9e86d8348236f2f1`, `truncated=false` e 3.285 entradas. Esse valor é uma
observação de validação, não uma revisão fixada; execuções futuras registram a revisão corrente.

O terceiro incremento foi validado no fluxo completo pela execução
`7409579a-695a-425a-afd7-c60a843a7496`, incluindo conteúdo seguro, citações, fontes persistidas e
bloqueio do piloto privado.

Em 19/10/2026, a execução `df985c6a-df0b-423d-9c4d-68f38f93f5a9` revalidou o fluxo público após a
inclusão da auditoria persistente de acesso a evidências. O laboratório confirmou um registro
`COMPLETED` com revisão, identidade da execução, `visibility: public` e `authenticated: false`, além
de um registro `DENIED` para a tentativa privada sem credencial.

## Estado do piloto privado

O acesso autenticado somente leitura está integrado ao transporte GitHub, com credencial em arquivo
secreto para Compose e escopo por repositório. A validação automatizada usa transporte simulado;
a identidade privada, visibilidade e branch `main` do repositório foram confirmadas em 16/10/2026
pela sessão GitHub local. A validação do fluxo completo permanece pendente de um token em arquivo de
escopo mínimo. O corpus
adversarial inicial está documentado em
[avaliacao-adversarial-fase4.md](avaliacao-adversarial-fase4.md).
