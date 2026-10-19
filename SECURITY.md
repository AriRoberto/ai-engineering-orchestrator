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

A coleta GitHub aceita projetos `read-only` definidos nos YAMLs locais. O cliente não escolhe URLs.
O piloto público não exige token. O piloto privado `app-ams` só é elegível para leitura autenticada
quando `AIEO_GITHUB_PRIVATE_READ_REPOSITORY` corresponde ao repositório permitido e há uma
credencial configurada; a credencial não é encaminhada ao orquestrador, ao LLM nem ao contexto da
execução. Use token GitHub de escopo mínimo, limitado ao repositório e com permissão de conteúdo
somente leitura. Em containers, forneça-o por arquivo secreto montado, não por commit ou imagem.
Tentativas concluídas, negadas e falhas são auditadas por projeto sem armazenar credencial ou
cabeçalho de autenticação.
Árvores truncadas, caminhos inseguros, SHAs inválidos e arquivos acima dos limites são recusados ou
ignorados. Conteúdo só é baixado quando `include_content=true`, de um subconjunto textual limitado
e priorizado. O texto precisa ser UTF-8, recebe hash SHA-256 e passa por detecção conservadora de
prompt injection e redaction de padrões de segredo. Conteúdo suspeito fica em quarentena sem texto
persistido. Diretórios gerados ou de dependências vendorizadas são excluídos da seleção.

Redaction baseada em padrões reduz exposição acidental, mas não prova ausência de segredos. O
conteúdo aprovado ainda é dado não confiável e nunca é executado. Quando `include_content=true` e a
consolidação está habilitada, somente o contexto aprovado e limitado é apresentado ao provedor em
uma seção marcada como não confiável, com instrução explícita para não seguir comandos externos.
Essa separação não elimina avaliações adversariais antes do uso de um provedor real.

O corpus em `evals/evidence-security.yaml` testa casos benignos, prompt injection, evasões simples e
redaction. `make eval-fase4` exige 100% dos casos conhecidos e falha com código não zero em caso de
regressão. O guard normaliza Unicode, remove caracteres invisíveis conhecidos e compacta whitespace
antes da análise. O corpus reduz risco conhecido, mas não constitui garantia de segurança completa.
