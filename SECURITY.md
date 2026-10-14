# Política de segurança

Não reporte vulnerabilidades em issues públicas. Use o relatório privado de vulnerabilidades do
GitHub quando estiver habilitado. Nunca faça commit de credenciais; segredos locais devem ficar no
arquivo `.env`, que é ignorado pelo Git.

O serviço opera somente para leitura por padrão. Solicitações de escrita param em
`WAITING_APPROVAL`. Branches protegidas, force push e merge automático são bloqueados pelo
`GitGovernanceService`. Esta fundação não executa comandos arbitrários no host nem aceita
credenciais de repositórios.

