# Runbook — erros HTTP 5xx

Alerta: `AIEOHighErrorRate`.

1. identifique rotas e status afetados sem adicionar identificadores de alta cardinalidade;
2. correlacione logs por `request_id`, `trace_id` e `execution_id`;
3. confira PostgreSQL, provedor LLM, GitHub e exportador OTLP conforme a rota;
4. compare a taxa com deploys e alterações de configuração recentes;
5. desabilite integrações opcionais ou reverta a versão quando isso reduzir impacto com segurança;
6. valide a recuperação por pelo menos duas janelas de cinco minutos.

Não copie conteúdo de evidência, prompts ou credenciais para o registro do incidente.
