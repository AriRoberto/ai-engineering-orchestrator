# Runbooks operacionais

Use estes runbooks a partir dos alertas versionados. Toda resposta deve preservar evidências e
evitar registrar prompts, chaves, conteúdo protegido ou dados pessoais.

## Processo de incidente

1. confirmar o alerta no Prometheus e o impacto no dashboard;
2. declarar severidade e responsável pela coordenação;
3. registrar horários, `request_id`, `trace_id`, versão e ações executadas;
4. mitigar com a menor mudança reversível possível;
5. validar `/health`, `/ready`, taxa de erro e consumo do orçamento;
6. comunicar encerramento e abrir análise pós-incidente quando aplicável.

| Severidade | Critério inicial | Resposta |
|---|---|---|
| SEV-1 | indisponibilidade ampla ou risco de segurança/dados | imediata, congelar mudanças |
| SEV-2 | degradação relevante ou consumo rápido de orçamento | até 15 minutos |
| SEV-3 | impacto limitado ou consumo sustentado | mesmo dia útil |

- [Disponibilidade e orçamento](disponibilidade.md)
- [Erros HTTP](erros-http.md)
- [Latência](latencia.md)

Nunca faça rollback destrutivo, remova volumes ou revele segredos durante a investigação. Incidentes
de segurança seguem também a política em [SECURITY.md](../../../SECURITY.md).
