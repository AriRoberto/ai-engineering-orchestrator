import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ContentAssessment:
    allowed: bool
    reasons: tuple[str, ...]


class KnowledgeContentGuard:
    patterns = (
        re.compile(r"ignore (all|any|the) previous instructions", re.IGNORECASE),
        re.compile(r"ignore todas? as instruções", re.IGNORECASE),
        re.compile(r"system prompt", re.IGNORECASE),
        re.compile(r"exfiltrat(e|ion)|exfiltrar", re.IGNORECASE),
        re.compile(r"reveal (the )?(secret|token|credential)", re.IGNORECASE),
    )

    def assess(self, content: str) -> ContentAssessment:
        reasons = tuple(pattern.pattern for pattern in self.patterns if pattern.search(content))
        return ContentAssessment(allowed=not reasons, reasons=reasons)
