# Política de segurança

Não reporte vulnerabilidades em issues públicas. Use o relatório privado de vulnerabilidades do
GitHub quando estiver habilitado. Nunca faça commit de credenciais; segredos locais devem ficar no
arquivo `.env`, que é ignorado pelo Git.

O serviço opera somente para leitura por padrão. Solicitações de escrita param em
`WAITING_APPROVAL`. Branches protegidas, force push e merge automático são bloqueados pelo
`GitGovernanceService`. Esta fundação não executa comandos arbitrários no host nem aceita
credenciais de repositórios.

Ferramentas MCP são negadas por padrão. Cada projeto possui uma allowlist de nomes qualificados,
entradas e saídas são validadas por schema e toda tentativa é auditada. Ferramentas destrutivas são
bloqueadas; ferramentas de escrita exigem revisão humana e não podem operar em projetos
`read-only`. O servidor do laboratório é simulado e não recebe credenciais nem acesso à rede.

O agente de Segurança da Fase 3 examina somente nomes de arquivos fornecidos como evidência. Ele não
lê segredos, não abre arquivos locais e não substitui análise de dependências, SAST ou revisão humana.

