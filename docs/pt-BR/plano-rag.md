# Plano de RAG — AI Engineering Orchestrator

Análise inicial do código local em 28/10/2026. O diagnóstico abaixo registra a linha de base anterior à implementação.

A primeira etapa já tem implementação local: scanner de revisão Git, prévia, proveniência,
fragmentos que preservam linhas e sincronização transacional por projeto/coleção.
Consulte [RAG de repositórios](rag-repositorio.md) para migração e operação.
A fragmentação inicial é por linhas. Embeddings semânticos opcionais e busca SQL
também estão implementados; consulte [RAG semântica](rag-semantica.md). Estrutura por
AST/seções, avaliação de relevância e as etapas seguintes permanecem pendentes.
Escopo proposto: consultar o próprio orquestrador e apoiar os projetos cadastrados,
mantendo bases isoladas. Os repositórios externos não foram inspecionados.

## O que já existe

| Componente | Local | Situação |
| --- | --- | --- |
| Ingestão, busca e exclusão HTTP | `apps/api/main.py` | Rotas `/v1/knowledge/*` disponíveis |
| Fragmentação e recuperação | `src/ai_engineering/knowledge/service.py` | Fragmentos de 800 caracteres com sobreposição de 100; remove indentação e quebras |
| Embeddings | `DeterministicEmbeddingProvider` | Hash em 16 dimensões, explicitamente para demonstração |
| Persistência | `knowledge/database.py`, migração 001 | PostgreSQL com `vector(16)` |
| Busca | `KnowledgeService.search` | Carrega fragmentos elegíveis e calcula ranking em Python; não usa o GIN textual existente |
| Integração | `orchestrator/service.py` | Recupera três trechos para consolidação; não os entrega individualmente aos especialistas |
| Evidências GitHub | `evidence/service.py` | Contexto citado por execução; não alimenta automaticamente a base de conhecimento |
| Isolamento | Repositórios e autorização HTTP | Escopo por projeto e compartilhamento explícito; orquestrador usa `include_shared=True` |
| Feedback | `/v1/feedback` | Armazenado, sem promoção automática a solução validada |
| Geração | Provedor padrão simulado | Demonstra o fluxo, não uma resposta semântica real |

Os caminhos abreviados estão sob `src/ai_engineering/`.

## Conteúdo da base

| Coleção | Fontes | Tratamento |
| --- | --- | --- |
| Arquitetura | README, ADRs e guia de arquitetura | Separar por títulos e registrar decisões |
| Implementação | `src/`, `apps/`, `web/src/` | Fragmentar por função, classe ou componente, preservando linhas |
| Persistência e contratos | Modelos e `migrations/` | Manter contexto de tabela, campo e versão |
| Operação | Runbooks, SLO, `k8s/`, Compose, observabilidade | Identificar ambiente; configuração não prova estado real |
| Validação | Testes, scripts, CI e avaliações | Distinguir testes disponíveis de testes executados |
| Histórico | Changelog, planos e laboratórios | Marcar proposta/histórico para não confundir com implementação |
| Projetos externos | Catálogo `configs/projects/` | Ingerir separadamente o conteúdo autorizado de cada repositório |

Usar `project_id=ai-engineering-orchestrator` para o próprio repositório.
Manter `app-financas` e `app-ams` isolados. Compartilhar somente práticas revisadas
com autorização explícita, nunca toda a base privada.

Excluir `.git`, dependências, caches, builds, binários, logs, `.env` e credenciais.
Inspecionar e sanitizar também exemplos e manifestos. Exemplos adversariais em
testes/evals precisam de tratamento separado: podem contaminar contexto ou ser
rejeitados pelo guard atual. Não desabilitar a proteção para forçar sua ingestão.

## Arquitetura proposta

```text
Arquivos versionados / coleta autorizada
  → seleção e revisão fixa
  → redaction e quarentena
  → fragmentos estruturados com linhas e títulos
  → embeddings semânticos em lotes
  → PostgreSQL: conteúdo, metadados, vetores e busca textual

Pergunta + identidade + projeto autorizado
  → candidatos textuais e vetoriais no escopo permitido
  → fusão de rankings e deduplicação
  → contexto limitado com fontes
  → consolidação e declaração de evidência insuficiente
```

Manter PostgreSQL/pgvector e os contratos existentes. A documentação oficial descreve
busca híbrida com full-text e Reciprocal Rank Fusion (RRF):
https://github.com/pgvector/pgvector#hybrid-search
Começar com busca vetorial exata em SQL; avaliar HNSW após medir volume, latência
e recuperação com filtros por projeto.

## Implementação em etapas

### 1. Ingestão local reproduzível

Criar um comando com prévia, caminhos permitidos, limites e relatório de arquivos
aceitos/ignorados/quarentenados. Ler arquivos rastreados pelo Git, sem seguir links
para fora da raiz. Identificar mudanças locais para não atribuí-las a um commit
que não contém essas mudanças.

Adicionar metadados: projeto, caminho, revisão, hash do conteúdo sanitizado, tipo,
data de indexação, modelo/dimensão/versão do embedding e versão do fragmentador.
Cada fragmento deve incluir linhas, seção e símbolo quando aplicáveis.

Implementar upsert e publicação transacional da versão ativa. Reindexar conteúdo
igual não deve duplicá-lo. Remover arquivos da versão ativa somente depois de uma
sincronização completa bem-sucedida; uma coleta parcial não deve apagar a base.

Aceite: duas ingestões iguais não duplicam; alteração e exclusão atualizam somente
o projeto correto; prévia não grava dados.

### 2. Embeddings semânticos

Introduzir um protocolo de embeddings e manter o determinístico para testes.
Escolher modelo avaliado em português e código conforme recursos disponíveis e
política de envio de conteúdo privado. Modelo e dimensão permanecem decisões pendentes.

Usar o mesmo modelo para documentos e consultas. Não misturar modelos, mesmo com
dimensões iguais. Criar nova migração e reconstruir os embeddings em uma versão
separada antes da troca. Alterar apenas `embedding_dimensions` não resolve:
a migração e o ORM estão fixos em 16 dimensões.

Aceite: paráfrases recuperam as fontes esperadas; dimensões/versões incompatíveis
são rejeitadas; falhas do provedor não publicam índice parcial.

### 3. Busca no banco

Adicionar busca ao contrato de repositório, mantendo implementação em memória
para testes. Aplicar autorização nas buscas textual e vetorial antes da seleção
dos resultados. Avaliar português para prosa e configuração `simple` para código.
Combinar rankings por RRF e avaliar qualidade antes de adicionar reranker.

Limitar candidatos e diversificar fontes. Não interpretar score como probabilidade
de correção. Calibrar a política de evidência insuficiente com perguntas sem resposta.

Aceite: não carregar toda a base em Python; medir Recall@5 e latência; nenhum trecho
privado de outro projeto deve aparecer.

### 4. Contexto e geração

Criar construtor de contexto de conhecimento análogo ao `EvidenceContextBuilder`.
Vincular citações a fragmento, revisão e linhas. Tratar todo conteúdo recuperado
como dado não confiável; a instrução atual destaca especificamente `[evidence:*]`.

Distribuir orçamento entre pergunta, conhecimento, evidências e resultados dos
agentes antes de chamar o modelo. Hoje o excesso pode interromper a consolidação.
Validar existência das citações e avaliar se sustentam as afirmações.

Integrar primeiro à consolidação. Para especialistas usarem os trechos, alterar
seus contratos explicitamente; hoje recebem o `TaskRequest` sem esse enriquecimento.

Aceite: resposta apoiada nas fontes; perguntas sem suporte recebem declaração de
evidência insuficiente; contexto não excede o orçamento.

### 5. Sincronização externa e operação

Conectar evidências GitHub aceitas/sanitizadas à ingestão, com revisão, visibilidade
e auditoria. A coleta atual tem limites de arquivos e bytes: não equivale à
indexação integral dos repositórios.

Medir idade do índice, pendências, latência, recuperação e consumo do provedor.
Não registrar texto privado ou segredos em métricas/logs. Promover feedback a
conhecimento somente após revisão explícita.

## Experimento com as APIs existentes

Com a aplicação disponível no Compose padrão, estes exemplos exercitam somente
o fluxo de demonstração. Não indexam o repositório inteiro nem validam qualidade
semântica. Se autenticação estiver habilitada, incluir a credencial configurada
e a autorização para o projeto.

```bash
curl --fail-with-body http://localhost:8000/v1/knowledge/documents \
  -H 'Content-Type: application/json' \
  -d '{"project_id":"ai-engineering-orchestrator","title":"Persistência","source":"repo://ai-engineering-orchestrator/src/ai_engineering/knowledge/database.py","content":"O conhecimento é persistido nas tabelas knowledge_documents e knowledge_chunks. O repositório PostgreSQL armazena embeddings em vector(16).","scope":"project","sharing_authorized":false}'

curl --fail-with-body http://localhost:8000/v1/knowledge/search \
  -H 'Content-Type: application/json' \
  -d '{"project_id":"ai-engineering-orchestrator","query":"Onde ficam os fragmentos de conhecimento?","limit":5,"include_shared":false}'
```

A ingestão atual cria documentos novos a cada chamada. Guardar o ID retornado e
excluir o documento de experimento pela rota
`DELETE /v1/knowledge/documents/{id}?project_id=ai-engineering-orchestrator`
antes de repetir a ingestão.

## Avaliação com perguntas do próprio projeto

| Pergunta | Fonte esperada |
| --- | --- |
| Como se impede compartilhamento não autorizado? | Serviço de conhecimento e seus testes |
| A busca consulta o índice textual do PostgreSQL? | Serviço, repositório e migração 001 |
| O que acontece se a tarefa solicita escrita? | Serviço do orquestrador |
| Como as evidências recebem citações? | Construtor de contexto e ADR-005 |
| Quais controles são exigidos em produção? | Settings e documentação de homologação |
| Qual foi a disponibilidade real do serviço ontem? | Sem resposta apenas com código e runbooks |

Medir Recall@5, posição da primeira fonte relevante, fidelidade de citações,
abstenção e latência p95. Incluir isolamento, atualização, remoção, redaction,
texto adversarial e orçamento de contexto. Definir metas após medir a linha de base.

## Situação de implementação

A ingestão local descrita no guia foi implementada sem alterar a ingestão manual existente.
A migração 005 adiciona proveniência, coleção e linhas dos fragmentos. A aplicação
usa embeddings determinísticos por padrão, com provedor OpenAI opcional e recuperação
híbrida SQL. A migração 006 permite versões com dimensões diferentes sem misturar
vetores. Ainda faltam avaliação semântica no corpus real, orçamento de contexto,
citações verificadas e sincronização GitHub antes de afirmar qualidade de produção.

