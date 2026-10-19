import re
import unicodedata
from dataclasses import dataclass


@dataclass(frozen=True)
class ContentAssessment:
    allowed: bool
    reasons: tuple[str, ...]


class KnowledgeContentGuard:
    patterns = (
        re.compile(r"ignore (all|any|the) (previous|prior) instructions", re.IGNORECASE),
        re.compile(r"ignore todas? as instruções( anteriores)?", re.IGNORECASE),
        re.compile(r"system prompt", re.IGNORECASE),
        re.compile(r"(begin|início) (system|sistema) (message|mensagem)", re.IGNORECASE),
        re.compile(r"exfiltrat(e|ion)|exfiltrar", re.IGNORECASE),
        re.compile(r"reveal (the )?(secret|token|credential)", re.IGNORECASE),
        re.compile(r"revele? (o )?(segredo|token|credencial)", re.IGNORECASE),
    )

    def assess(self, content: str) -> ContentAssessment:
        normalized = unicodedata.normalize("NFKC", content)
        normalized = re.sub(r"[\u200b-\u200f\u2060\ufeff]", "", normalized)
        normalized = re.sub(r"\s+", " ", normalized)
        reasons = tuple(pattern.pattern for pattern in self.patterns if pattern.search(normalized))
        return ContentAssessment(allowed=not reasons, reasons=reasons)
