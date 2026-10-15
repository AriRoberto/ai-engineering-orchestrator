# ADR-004: Conteúdo textual controlado de evidências públicas

- Status: aceito para o segundo incremento da Fase 4
- Data: 15/10/2026

## Contexto

O inventário do ADR-003 comprova a existência e a revisão dos arquivos, mas não permite análise
semântica futura. Baixar conteúdo externo amplia riscos de volume, segredos acidentais, encoding
inválido e prompt injection. A evolução precisa manter a origem fixa, o menor privilégio e uma
trilha explícita do motivo pelo qual cada conteúdo foi ou não aceito.

## Decisão

A coleta de conteúdo é desabilitada por padrão e exige `include_content=true`. O coletor seleciona
um subconjunto priorizado do inventário previamente validado e aplica limites independentes de
quantidade, tamanho individual e tamanho total. O download usa exclusivamente a Contents API do
GitHub para o proprietário, repositório, branch e caminho já derivados da configuração confiável.
Diretórios gerados e dependências vendorizadas são excluídos antes de consumir o orçamento.

Somente UTF-8 é aceito. O conteúdo bruto recebe SHA-256 e, antes da persistência, passa por uma
defesa conservadora contra prompt injection e por redaction de padrões comuns de credenciais. Cada
arquivo registra `content_status`. Conteúdo em quarentena não é persistido; somente seu hash e seus
metadados permanecem para auditoria.

Neste incremento, texto aprovado continua sendo dado não confiável. Seu uso posterior no contexto
de análise é governado pelo ADR-005. Segurança e Documentação também consomem contagens e estados.

## Consequências

- o piloto público fornece evidência textual reproduzível sem executar o repositório;
- a superfície de dados aumenta, mas permanece opt-in e limitada;
- redaction reduz exposição acidental, sem garantir detecção completa de segredos;
- falsos positivos de prompt injection são aceitos em favor de falha fechada;
- análise semântica com citações requer uma decisão e avaliações adicionais.

## Referências

- [ADR-003 — coleta governada de evidências públicas](ADR-003-governed-public-evidence.md)
- [Repository contents API](https://docs.github.com/pt/rest/repos/contents?apiVersion=2022-11-28)
- [ADR-005 — contexto citado de evidências externas](ADR-005-cited-evidence-context.md)
