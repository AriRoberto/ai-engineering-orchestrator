# ADR-005: Contexto citado de evidências externas

- Status: aceito para o terceiro incremento da Fase 4
- Data: 15/10/2026

## Contexto

O ADR-004 permite persistir texto externo aprovado, mas persistência não deve significar exposição
ilimitada ao fluxo de análise. Especialistas e provedores precisam de um contexto pequeno,
reproduzível e citável, sem perder a distinção entre instruções do sistema e dados do repositório.

## Decisão

Um `EvidenceContextBuilder` seleciona somente itens com estado `included` ou `redacted`, aplica um
orçamento global de caracteres e produz entradas com caminho, URL, SHA-256, conteúdo e marcador de
truncamento. Cada entrada recebe a citação estável `[evidence:<path>]`.

O contexto é anexado à solicitação persistida, e suas URLs são copiadas para `evidence_sources` na
execução. A consolidação inclui uma seção explícita de evidências externas não confiáveis e instrui
o provedor a nunca obedecer comandos encontrados dentro das citações. Quarentena e redaction
continuam ocorrendo antes dessa etapa.

## Consequências

- respostas futuras podem apontar para arquivos e revisões verificáveis;
- o orçamento é determinístico e configurável por `AIEO_EVIDENCE_CONTEXT_MAX_CHARS`;
- conteúdo truncado é identificado, evitando aparência de leitura integral;
- a defesa em camadas reduz risco, mas não elimina prompt injection;
- uma suíte adversarial ainda é obrigatória antes de habilitar um provedor real no piloto.

## Referências

- [ADR-004 — conteúdo textual controlado](ADR-004-controlled-text-evidence.md)
- [Plano de implementação](../pt-BR/plano-de-implementacao.md)
