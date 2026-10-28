# RAG semântica e recuperação SQL

O provedor de embeddings é independente do provedor de geração de respostas.
O padrão continua `deterministic`, sem chamadas externas. Para usar embeddings
semânticos, configure explicitamente `openai`. Esta integração foi validada com
clientes simulados; qualidade, custo e disponibilidade na conta precisam de uma
avaliação com o corpus antes de uso em produção.

## Migração e versões

A migração `006_semantic_knowledge.sql` preserva os vetores existentes, remove
somente a dimensão fixa da coluna e identifica os documentos antigos como
`deterministic:deterministic-demo:1:16`. Ela não converte vetores em embeddings
semânticos. Reindexe o corpus para produzir os novos vetores.

Cada índice é identificado por provedor, modelo, versão e dimensão. A ingestão
publica atomicamente apenas a versão selecionada da coleção; versões anteriores
continuam disponíveis. A configuração do provedor na API seleciona a versão que
será consultada. Não existe fallback automático para outro modelo: se ainda não
houver documentos naquela versão, a busca retorna lista vazia.

Para atualizar uma demo existente, mantenha seus arquivos Compose de OpenAI/acesso
privado, reconstrua a imagem e execute `python -m ai_engineering.infrastructure.migrations`
em um container administrativo antes de recriar a API. O banco deve estar ativo.
Não remova volumes nem altere manualmente os vetores antigos.

## Configuração semântica

```dotenv
AIEO_EMBEDDING_PROVIDER=openai
AIEO_EMBEDDING_MODEL=text-embedding-3-small
AIEO_EMBEDDING_DIMENSIONS=1536
AIEO_EMBEDDING_BATCH_SIZE=32
AIEO_EMBEDDING_TIMEOUT_SECONDS=30
AIEO_OPENAI_API_KEY_FILE=/run/secrets/openai_api_key
```

Use o mecanismo de segredo existente em `compose.demo.openai.yaml` para montar
a chave, ou um arquivo Compose equivalente se a geração continuar simulada.
O caminho do segredo precisa existir dentro do container. Uma chave GitHub não
autentica na API OpenAI. Não coloque a chave no repositório ou nos argumentos do CLI.

Faça primeiro a prévia do [guia de ingestão](rag-repositorio.md). A prévia permanece
local e usa o perfil demonstrativo; não envia trechos nem precisa de chave OpenAI.
No comando de publicação, configure o perfil acima e use `--apply`. Apenas esse
modo gera e envia os trechos sanitizados ao provedor. Isso pode gerar custos e
requer que o conteúdo seja autorizado para envio externo. A troca da configuração
da API deve ocorrer depois da reconstrução bem-sucedida do índice de cada projeto.

Todas as respostas de embeddings são validadas em quantidade, índices, dimensão
e valores finitos antes da publicação. Uma falha cancela a publicação e preserva
a versão anterior. Os lotes têm no máximo 32 trechos e cada trecho semântico tem
limite conservador de 8000 bytes UTF-8; ajuste o fragmentador quando necessário.

Para voltar ao perfil anterior, restaure `AIEO_EMBEDDING_PROVIDER=deterministic`
e `AIEO_EMBEDDING_DIMENSIONS=16` e recrie a API. Os documentos manuais existentes
não são reindexados automaticamente; envie-os novamente com o novo perfil se
também precisar deles na busca semântica.

## Recuperação

A implementação PostgreSQL executa no banco:

1. Filtro de autorização por projeto/compartilhamento e versão do embedding.
2. Seleção vetorial exata por distância de cosseno, sem carregar a base no Python.
3. Busca textual em português e `simple` para identificadores de código.
4. Fusão RRF, desempate por ID e limite final de resultados.

São selecionados até `max(20, limit * 4)` candidatos por modalidade. O score RRF
representa posição relativa nos rankings, não probabilidade de correção. O índice
textual `simple` complementa o GIN em português existente. O PostgreSQL escolhe o
plano de execução; esta etapa não adiciona HNSW nem promete uma latência específica.
O repositório em memória usa aproximação lexical por palavras para testes, sem
pretender reproduzir stemming e ranking textual do PostgreSQL.

Fontes oficiais usadas no contrato:

- [Embeddings OpenAI](https://developers.openai.com/api/reference/resources/embeddings/methods/create)
- [Busca híbrida pgvector](https://github.com/pgvector/pgvector#hybrid-search)

Próxima etapa: orçamento de contexto, citações verificadas e avaliação de recuperação
com perguntas e fontes esperadas. A separação por versão impede mistura de vetores,
mas não substitui a avaliação da relevância das respostas.
