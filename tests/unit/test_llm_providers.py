import pytest

from ai_engineering.integrations.llm.base import LLMRequest
from ai_engineering.integrations.llm.providers import SimulatedLLMProvider, build_llm_provider


def test_simulated_provider_is_explicitly_marked() -> None:
    result = SimulatedLLMProvider().generate(LLMRequest(instructions="Teste", prompt="Olá"))
    assert result.simulated is True
    assert result.provider == "simulated"
    assert "SIMULAÇÃO" in result.text


def test_unknown_provider_fails_closed() -> None:
    with pytest.raises(ValueError, match="não suportado"):
        build_llm_provider("desconhecido", "modelo")
