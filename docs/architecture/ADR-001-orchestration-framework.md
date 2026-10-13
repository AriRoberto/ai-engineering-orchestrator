# ADR-001: Deterministic core with OpenAI Agents SDK adapter

- Status: Accepted for Phase 1
- Date: 2026-10-13

## Context

The platform requires predictable policy enforcement, a no-credential demo mode, human approvals,
bounded execution and future LLM-driven delegation. LangGraph provides graph-oriented durable
workflows. The OpenAI Agents SDK provides a smaller Python-first abstraction set, manager-style
orchestration, handoffs, guardrails, tracing and usage data.

## Decision

Phase 1 uses a provider-neutral deterministic orchestrator written against internal agent contracts.
Phase 2 will add an OpenAI Agents SDK adapter behind those contracts. The deterministic policy and
Git-governance layers remain authoritative; an LLM never grants itself permission.

This choice keeps the demo free of paid dependencies, reduces lock-in at the domain boundary, and
aligns future manager-style agent orchestration with the platform's central orchestrator model.

## Consequences

- Phase 1 has no LLM dependency and does not claim autonomous reasoning.
- LangGraph remains a documented alternative if durable graph checkpoints become a stronger need.
- SDK integration, model configuration, cost accounting and tracing are Phase 2 work.

## References

- OpenAI Agents SDK: https://openai.github.io/openai-agents-python/
- Agent orchestration: https://openai.github.io/openai-agents-python/multi_agent/
- LangGraph overview: https://docs.langchain.com/oss/python/langgraph/overview

