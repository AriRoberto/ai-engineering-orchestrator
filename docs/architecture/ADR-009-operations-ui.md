# ADR-009 — Interface operacional integrada

- Estado: aceito
- Data: 19/10/2026

## Contexto

Operadores precisam consultar histórico, fontes, auditorias e aprovações sem montar chamadas HTTP
manualmente. A interface não deve criar uma segunda fonte de regras nem receber privilégios
superiores aos oferecidos pela API.

## Decisão

Construir uma aplicação React estática, compilada por Vite e servida pela própria FastAPI em `/ui/`.
A interface chama exclusivamente endpoints `/v1`, envia `X-API-Key` quando fornecida e mantém a
chave apenas em `sessionStorage`. Ela permite:

- consultar execuções e resultado consolidado;
- abrir fontes registradas;
- consultar auditoria de evidências;
- listar aprovações MCP pendentes e aprová-las com identidade explícita.

O backend ganha uma operação de aprovação por ID. Ela recupera somente uma pendência do mesmo
projeto, impede reprocessamento e registra `approval_of` no novo evento auditável.

## Consequências

- frontend e backend são entregues na mesma imagem e versão;
- autorização permanece integralmente no servidor;
- a chave não é persistida além da aba, mas continua acessível ao JavaScript da página;
- produção deve substituir API key digitada por sessão segura com identidade federada e proteção
  adicional contra XSS/CSRF conforme o modelo de autenticação adotado.
