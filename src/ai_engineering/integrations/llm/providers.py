from ai_engineering.integrations.llm.base import LLMRequest, LLMResponse, LLMUsage
from ai_engineering.security.credentials import read_secret_file


def estimate_tokens(text: str) -> int:
    """Estimativa conservadora e explícita; não substitui o tokenizer do provedor."""
    return max(1, (len(text) + 3) // 4)


class SimulatedLLMProvider:
    """Provider determinístico para testes e demonstrações sem custo."""

    def generate(self, request: LLMRequest) -> LLMResponse:
        text = f"[SIMULAÇÃO] Solicitação recebida: {request.prompt[:200]}"
        return LLMResponse(
            text=text,
            provider="simulated",
            model="deterministic-demo",
            simulated=True,
            usage=LLMUsage(
                input_tokens=estimate_tokens(request.instructions + request.prompt),
                output_tokens=estimate_tokens(text),
            ),
        )


class OpenAIAgentsProvider:
    """Adaptador do Agents SDK, selecionado somente por configuração explícita."""

    def __init__(
        self,
        model: str,
        api_key: str | None = None,
        api_key_file: str | None = None,
        timeout_seconds: float = 60.0,
        store_responses: bool = False,
        tracing_enabled: bool = False,
    ) -> None:
        resolved_key = read_secret_file(api_key_file) if api_key_file else (api_key or "").strip()
        if not resolved_key:
            raise ValueError(
                "openai-agents exige AIEO_OPENAI_API_KEY_FILE ou AIEO_OPENAI_API_KEY"
            )
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.store_responses = store_responses
        self.tracing_enabled = tracing_enabled
        from openai import AsyncOpenAI

        self._client = AsyncOpenAI(api_key=resolved_key, timeout=timeout_seconds)

    def generate(self, request: LLMRequest) -> LLMResponse:
        from agents import Agent, ModelSettings, OpenAIResponsesModel, RunConfig, Runner

        agent = Agent(
            name="Assistente de engenharia",
            instructions=request.instructions,
            model=OpenAIResponsesModel(model=self.model, openai_client=self._client),
            model_settings=ModelSettings(
                max_tokens=request.max_output_tokens,
                store=self.store_responses,
                include_usage=True,
                timeout=self.timeout_seconds,
            ),
        )
        result = Runner.run_sync(
            agent,
            request.prompt,
            run_config=RunConfig(tracing_disabled=not self.tracing_enabled),
        )
        usage = result.context_wrapper.usage
        return LLMResponse(
            text=str(result.final_output),
            provider="openai-agents",
            model=self.model,
            simulated=False,
            usage=LLMUsage(
                input_tokens=usage.input_tokens,
                output_tokens=usage.output_tokens,
                estimated=False,
            ),
        )


def build_llm_provider(
    provider: str,
    model: str,
    *,
    api_key: str | None = None,
    api_key_file: str | None = None,
    timeout_seconds: float = 60.0,
    store_responses: bool = False,
    tracing_enabled: bool = False,
):
    if provider == "simulated":
        return SimulatedLLMProvider()
    if provider == "openai-agents":
        return OpenAIAgentsProvider(
            model,
            api_key=api_key,
            api_key_file=api_key_file,
            timeout_seconds=timeout_seconds,
            store_responses=store_responses,
            tracing_enabled=tracing_enabled,
        )
    raise ValueError(f"Provedor de LLM não suportado: {provider}")
