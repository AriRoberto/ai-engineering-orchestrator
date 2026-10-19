import re
from dataclasses import dataclass


@dataclass(frozen=True)
class RedactionResult:
    content: str
    redactions: int


class SecretRedactor:
    patterns = (
        re.compile(r"(?i)(api[_-]?key|token|secret|password)\s*[:=]\s*['\"]?[^\s'\"]{8,}"),
        re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}"),
        re.compile(r"AKIA[0-9A-Z]{16}"),
        re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    )

    def redact(self, content: str) -> RedactionResult:
        redactions = 0
        sanitized = content
        for pattern in self.patterns:
            sanitized, count = pattern.subn("[REDACTED]", sanitized)
            redactions += count
        return RedactionResult(content=sanitized, redactions=redactions)
