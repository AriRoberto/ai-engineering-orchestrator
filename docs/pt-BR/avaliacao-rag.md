# Avaliação e aprendizado da RAG

Este fluxo permite ensinar o sistema por exemplos verificáveis sem alterar pesos de modelos.
Cada caso associa uma pergunta a uma ou mais fontes que um especialista considera corretas.
A recuperação é executada com a configuração ativa e o resultado fica vinculado ao projeto,
à revisão Git e ao embedding utilizado.

## Como criar um caso

1. Abra `http://localhost:8000/ui/` e selecione **Base RAG**.
2. Confirme que o inventário está marcado como **PRONTA**.
3. Em **Avaliação RAG com resposta esperada**, escolha a especialidade.
4. Escreva uma pergunta real que o agente deverá responder.
5. Informe um caminho esperado por linha, por exemplo
   `backend/migrations/001_members_and_transactions.sql`.
6. Execute a avaliação e inspecione os cinco primeiros trechos.
7. Classifique cada trecho como relevante, parcial ou irrelevante.

O caminho esperado pode ser a fonte `repo://` completa ou o caminho final dentro do
repositório. O sistema não considera texto de resposta como gabarito: a evidência esperada
é sempre uma fonte rastreável.

## Métricas

- **Hit@1:** a primeira recuperação contém uma fonte esperada.
- **Hit@3:** uma fonte esperada aparece entre as três primeiras.
- **Hit@5:** uma fonte esperada aparece entre as cinco primeiras.
- **MRR:** média do inverso da posição do primeiro resultado relevante. Quanto mais próximo
  de `1`, melhor a ordenação.
- **Feedback:** contagem das classificações humanas dos chunks recuperados.

Um único caso com 100% não demonstra qualidade geral. Como ponto de partida, crie pelo
menos cinco perguntas por especialidade e inclua casos em que documentos tenham termos
parecidos, mas respostas diferentes.

## Ordem recomendada para o app-financas

1. Banco de dados: schema, migrações, persistência e restauração.
2. Segurança: autenticação, validação de entrada, segredos e dependências.
3. QA: testes unitários, integração e cenários financeiros críticos.
4. Arquitetura: fronteiras entre frontend, backend e armazenamento.
5. Operação: Docker, inicialização, health checks e recuperação.
6. Documentação: instalação, configuração e limitações conhecidas.

## Como usar os resultados

Não ajuste chunking ou embeddings a partir de uma impressão isolada. Compare métricas para
o mesmo conjunto de casos e revisão. A ordem segura de ajustes é:

1. corrigir fontes ausentes ou indevidamente excluídas da ingestão;
2. melhorar a formulação da pergunta e o gabarito;
3. ajustar fragmentação;
4. ajustar a fusão lexical/vetorial;
5. avaliar embeddings semânticos;
6. somente depois revisar prompts dos agentes ou considerar fine-tuning.

Os embeddings determinísticos atuais validam o processo e a busca híbrida, mas não são um
modelo semântico treinável. Ao ativar embeddings externos, mantenha os mesmos casos para
comparar a mudança objetivamente.
