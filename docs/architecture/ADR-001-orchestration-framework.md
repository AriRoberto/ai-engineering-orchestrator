# ADR-001: Núcleo determinístico com adaptador do OpenAI Agents SDK

- Status: aceito para a Fase 1
- Data: 13/10/2026

## Contexto

A plataforma exige aplicação previsível de políticas, modo demonstração sem credenciais, aprovações
humanas, execução limitada e futura delegação dirigida por LLM. O LangGraph oferece fluxos duráveis
orientados a grafos. O OpenAI Agents SDK oferece um conjunto menor de abstrações centradas em
Python, orquestração no padrão gerente, transferências, proteções, rastreamento e dados de uso.

## Decisão

A Fase 1 usa um orquestrador determinístico e neutro em relação a provedores, escrito sobre
contratos internos de agentes. A Fase 2 adicionará um adaptador do OpenAI Agents SDK por trás desses
contratos. As camadas determinísticas de políticas e governança Git continuam sendo a autoridade;
um LLM nunca concede permissão a si mesmo.

Essa escolha mantém a demonstração livre de dependências pagas, reduz o acoplamento na fronteira do
domínio e alinha a futura orquestração no padrão gerente ao modelo de orquestrador central.

## Consequências

- A Fase 1 não depende de LLM nem alega raciocínio autônomo.
- O LangGraph permanece como alternativa documentada caso checkpoints duráveis em grafo se tornem
  uma necessidade prioritária.
- Integração do SDK, configuração de modelos, contabilização de custos e rastreamento pertencem à
  Fase 2.

## Referências

- OpenAI Agents SDK: https://openai.github.io/openai-agents-python/
- Orquestração de agentes: https://openai.github.io/openai-agents-python/multi_agent/
- Visão geral do LangGraph: https://docs.langchain.com/oss/python/langgraph/overview

