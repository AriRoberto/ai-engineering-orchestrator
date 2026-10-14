from ai_engineering.integrations.llm.base import LLMRequest, LLMResponse


class SimulatedLLMProvider:
    """Provider determinístico para testes e demonstrações sem custo."""

    def generate(self, request: LLMRequest) -> LLMResponse:
        return LLMResponse(
            text=f"[SIMULAÇÃO] Solicitação recebida: {request.prompt[:200]}",
            provider="simulated",
            model="deterministic-demo",
            simulated=True,
        )


class OpenAIAgentsProvider:
    """Adaptador do Agents SDK, selecionado somente por configuração explícita."""

    def __init__(self, model: str) -> None:
        self.model = model

    def generate(self, request: LLMRequest) -> LLMResponse:
        from agents import Agent, ModelSettings, Runner

        agent = Agent(
            name="Assistente de engenharia",
            instructions=request.instructions,
            model=self.model,
            model_settings=ModelSettings(max_tokens=request.max_output_tokens),
        )
        result = Runner.run_sync(agent, request.prompt)
        return LLMResponse(
            text=str(result.final_output),
            provider="openai-agents",
            model=self.model,
            simulated=False,
        )


def build_llm_provider(provider: str, model: str):
    if provider == "simulated":
        return SimulatedLLMProvider()
    if provider == "openai-agents":
        return OpenAIAgentsProvider(model)
    raise ValueError(f"Provedor de LLM não suportado: {provider}")
