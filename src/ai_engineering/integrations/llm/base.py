from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class LLMRequest:
    instructions: str
    prompt: str
    max_output_tokens: int = 1_000


@dataclass(frozen=True)
class LLMUsage:
    input_tokens: int
    output_tokens: int
    estimated: bool = True
    estimated_cost_usd: float | None = None


@dataclass(frozen=True)
class LLMResponse:
    text: str
    provider: str
    model: str
    simulated: bool
    usage: LLMUsage


class LLMProvider(Protocol):
    def generate(self, request: LLMRequest) -> LLMResponse: ...
