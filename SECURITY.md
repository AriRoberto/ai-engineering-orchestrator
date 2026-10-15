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

O agente de Segurança da Fase 3 examina nomes de arquivos e estados de proteção da evidência. Ele
não recebe conteúdo em quarentena, não substitui análise de dependências, SAST ou revisão humana e
não deve ser tratado como detector completo de segredos.

A coleta GitHub aceita apenas projetos públicos e `read-only` definidos nos YAMLs locais. O cliente
não escolhe URLs. Árvores truncadas, caminhos inseguros, SHAs inválidos e arquivos acima dos limites
são recusados ou ignorados. Conteúdo só é baixado quando `include_content=true`, de um subconjunto
textual limitado e priorizado. O texto precisa ser UTF-8, recebe hash SHA-256 e passa por detecção
conservadora de prompt injection e redaction de padrões de segredo. Conteúdo suspeito fica em
quarentena sem texto persistido. Diretórios gerados ou de dependências vendorizadas são excluídos
da seleção. O projeto privado `app-ams` permanece bloqueado sem autenticação.

Redaction baseada em padrões reduz exposição acidental, mas não prova ausência de segredos. O
conteúdo aprovado ainda é dado não confiável e, neste incremento, não é enviado automaticamente ao
LLM nem executado.

