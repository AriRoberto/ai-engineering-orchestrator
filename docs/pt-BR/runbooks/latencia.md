# Runbook — latência

Alerta: `AIEOHighP95Latency`.

1. confirme p50, p95, volume e saturação para distinguir lentidão de amostra pequena;
2. verifique CPU, memória, pool/conexões do PostgreSQL e dependências externas;
3. compare execuções diretas e baseadas em evidência;
4. preserve timeouts e limites; não os amplie como primeira mitigação;
5. reduza carga, desabilite integração opcional ou reverta mudança recente de forma controlada;
6. encerre após p95 abaixo de 2 s por duas janelas de dez minutos.

Registre a dependência dominante e o efeito da mitigação para orientar capacidade e otimização.
