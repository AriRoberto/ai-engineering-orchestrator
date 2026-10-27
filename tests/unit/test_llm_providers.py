from types import SimpleNamespace

import pytest

from ai_engineering.integrations.llm.base import LLMRequest
from ai_engineering.integrations.llm.providers import (
    OpenAIAgentsProvider,
    SimulatedLLMProvider,
    build_llm_provider,
)


def test_simulated_provider_is_explicitly_marked() -> None:
    result = SimulatedLLMProvider().generate(LLMRequest(instructions="Teste", prompt="Olá"))
    assert result.simulated is True
    assert result.provider == "simulated"
    assert "SIMULAÇÃO" in result.text
    assert result.usage.input_tokens > 0
    assert result.usage.output_tokens > 0
    assert result.usage.estimated is True


def test_unknown_provider_fails_closed() -> None:
    with pytest.raises(ValueError, match="não suportado"):
        build_llm_provider("desconhecido", "modelo")


def test_openai_provider_requires_explicit_credential(tmp_path) -> None:
    with pytest.raises(ValueError, match="AIEO_OPENAI_API_KEY_FILE"):
        OpenAIAgentsProvider("modelo", api_key_file=str(tmp_path / "missing"))


def test_openai_provider_uses_actual_sdk_usage_and_private_defaults(monkeypatch) -> None:
    from agents import Runner

    captured = {}

    def fake_run_sync(agent, prompt, *, run_config):
        captured["agent"] = agent
        captured["prompt"] = prompt
        captured["run_config"] = run_config
        return SimpleNamespace(
            final_output="Parecer técnico",
            context_wrapper=SimpleNamespace(
                usage=SimpleNamespace(input_tokens=31, output_tokens=17)
            ),
        )

    monkeypatch.setattr(Runner, "run_sync", fake_run_sync)
    provider = OpenAIAgentsProvider("modelo-real", api_key="test-key", timeout_seconds=12)
    result = provider.generate(LLMRequest(instructions="Seja direto", prompt="Analise"))

    assert result.simulated is False
    assert result.usage.input_tokens == 31
    assert result.usage.output_tokens == 17
    assert result.usage.estimated is False
    assert captured["prompt"] == "Analise"
    assert captured["agent"].model_settings.store is False
    assert captured["agent"].model_settings.include_usage is True
    assert captured["agent"].model_settings.timeout == 12
    assert captured["run_config"].tracing_disabled is True
