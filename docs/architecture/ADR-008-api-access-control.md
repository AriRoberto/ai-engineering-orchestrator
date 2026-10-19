# ADR-008 — Controle de acesso e quotas da API

- Estado: aceito
- Data: 19/10/2026

## Contexto

Os endpoints `/v1` precisam de uma fronteira de acesso independente do provedor de identidade
futuro. A solução deve falhar fechada, isolar projetos e limitar abuso sem introduzir chaves no
repositório, em logs ou em métricas.

## Decisão

Adicionar uma camada opcional de API keys com estas propriedades:

- ativação explícita por `AIEO_API_AUTH_ENABLED`;
- arquivo secreto obrigatório em `AIEO_API_KEYS_FILE` quando ativada;
- somente SHA-256 das chaves no arquivo, com comparação em tempo constante;
- papéis `viewer` para leitura e `operator` para leitura e mutação;
- allowlist de projetos por identidade, com `*` somente quando declarado;
- quota fixa por minuto e por `key_id`, com HTTP 429 e `Retry-After`;
- `/health`, `/metrics` e documentação OpenAPI permanecem públicos.

A ausência ou invalidade do arquivo impede a inicialização quando a autenticação está habilitada.
O modo permanece desligado por padrão para compatibilidade dos laboratórios existentes.

## Consequências

- a API pode ser exposta em ambientes controlados sem credencial global compartilhada;
- rotação consiste em trocar o arquivo secreto e reiniciar a instância;
- a quota em memória é local por réplica e serve como proteção inicial, não como quota distribuída;
- produção ainda requer TLS, identidade federada, armazenamento gerenciado e rate limiting global.
