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

O conteúdo coletado não é executado e ainda não é enviado automaticamente a um modelo. Os agentes
de Segurança e Documentação consomem apenas os estados de controle para produzir diagnósticos
honestos nesta etapa.

## Segurança e honestidade do resultado

O `project_id` não controla a URL remota. O destino vem de `configs/projects/app-financas.yaml` e o
transporte usa somente `https://api.github.com`. O projeto privado `app-ams` recebe HTTP 403.

Os achados indicam padrões derivados do inventário e dos estados de conteúdo, não uma revisão
semântica completa do código. O modo `demo` continua recomendado até que exista análise controlada
e rastreável do texto aprovado.

## Evidência de validação

Em 15/10/2026, a consulta real da branch `main` retornou a revisão
`9ed4c91ed1e29c0ccfe7d69f9e86d8348236f2f1`, `truncated=false` e 3.285 entradas. Esse valor é uma
observação de validação, não uma revisão fixada; execuções futuras registram a revisão corrente.

## Próximo incremento

O próximo passo é transformar o conteúdo aprovado em contexto mínimo para especialistas, com
orçamento por execução, citações por arquivo e avaliação que demonstre que o modelo não obedece a
instruções presentes na evidência.
