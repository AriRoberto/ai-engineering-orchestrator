# Runbook — disponibilidade e orçamento

Alertas: `AIEOApiUnavailable`, `AIEOAvailabilityBudgetFastBurn` e
`AIEOAvailabilityBudgetSlowBurn`.

1. confirme `up{job="ai-engineering-orchestrator"}`, `/health` e `/ready` separadamente;
2. se `/health` falhar, verifique estado, reinícios, recursos e logs dos pods;
3. se apenas `/ready` falhar, valide conectividade, credencial, capacidade e migrações do PostgreSQL;
4. compare a versão atual com a última versão saudável e pause novos deploys;
5. prefira rollback da imagem/configuração; não reverta migrações sem plano específico;
6. encerre somente após 15 minutos estáveis e redução do burn rate.

Evidências mínimas: início/fim, alertas, versão, réplicas prontas, mudança correlacionada, causa,
mitigação e links para métricas/traces. Escale como SEV-1 se todas as réplicas estiverem fora ou
houver risco de integridade; caso contrário, trate burn rápido como SEV-2 e burn lento como SEV-3.
