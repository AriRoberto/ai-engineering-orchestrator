from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class LLMRequest:
    instructions: str
    prompt: str
    max_output_tokens: int = 1_000


@dataclass(frozen=True)
class LLMResponse:
    text: str
    provider: str
    model: str
    simulated: bool


class LLMProvider(Protocol):
    def generate(self, request: LLMRequest) -> LLMResponse: ...
