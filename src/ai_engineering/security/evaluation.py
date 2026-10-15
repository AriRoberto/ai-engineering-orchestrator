from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from ai_engineering.evidence.models import EvidenceContextItem
from ai_engineering.security.content import KnowledgeContentGuard
from ai_engineering.security.secrets import SecretRedactor


@dataclass(frozen=True)
class AdversarialCase:
    id: str
    category: str
    content: str
    expected_status: str


@dataclass(frozen=True)
class AdversarialResult:
    id: str
    category: str
    expected_status: str
    actual_status: str
    passed: bool


@dataclass(frozen=True)
class AdversarialReport:
    total: int
    passed: int
    failed: int
    pass_rate: float
    threshold: float
    approved: bool
    categories: dict[str, dict[str, int]]
    results: tuple[AdversarialResult, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "total": self.total,
            "passed": self.passed,
            "failed": self.failed,
            "pass_rate": self.pass_rate,
            "threshold": self.threshold,
            "approved": self.approved,
            "categories": self.categories,
            "results": [result.__dict__ for result in self.results],
        }


class EvidenceSecurityEvaluator:
    valid_statuses = {"included", "quarantined", "redacted"}

    def __init__(
        self,
        guard: KnowledgeContentGuard | None = None,
        redactor: SecretRedactor | None = None,
        threshold: float = 1.0,
    ) -> None:
        if not 0 < threshold <= 1:
            raise ValueError("O limiar deve estar entre zero e um")
        self.guard = guard or KnowledgeContentGuard()
        self.redactor = redactor or SecretRedactor()
        self.threshold = threshold

    def evaluate(self, cases: list[AdversarialCase]) -> AdversarialReport:
        if not cases:
            raise ValueError("O corpus adversarial não pode ser vazio")
        results = tuple(self._evaluate_case(case) for case in cases)
        passed = sum(result.passed for result in results)
        pass_rate = passed / len(results)
        categories: dict[str, dict[str, int]] = {}
        for result in results:
            metrics = categories.setdefault(result.category, {"total": 0, "passed": 0})
            metrics["total"] += 1
            metrics["passed"] += int(result.passed)
        return AdversarialReport(
            total=len(results),
            passed=passed,
            failed=len(results) - passed,
            pass_rate=pass_rate,
            threshold=self.threshold,
            approved=pass_rate >= self.threshold,
            categories=categories,
            results=results,
        )

    def _evaluate_case(self, case: AdversarialCase) -> AdversarialResult:
        if case.expected_status not in self.valid_statuses:
            raise ValueError(f"Status esperado inválido no caso {case.id}")
        assessment = self.guard.assess(case.content)
        if not assessment.allowed:
            actual_status = "quarantined"
        else:
            redacted = self.redactor.redact(case.content)
            actual_status = "redacted" if redacted.redactions else "included"
        return AdversarialResult(
            id=case.id,
            category=case.category,
            expected_status=case.expected_status,
            actual_status=actual_status,
            passed=actual_status == case.expected_status,
        )


def load_adversarial_cases(path: str | Path) -> list[AdversarialCase]:
    payload = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    raw_cases = payload.get("cases", [])
    if not isinstance(raw_cases, list):
        raise ValueError("Corpus adversarial inválido")
    return [AdversarialCase(**item) for item in raw_cases]


def validate_evidence_context(
    items: list[EvidenceContextItem], max_chars: int
) -> tuple[str, ...]:
    errors: list[str] = []
    if sum(len(item.content) for item in items) > max_chars:
        errors.append("context-budget-exceeded")
    citations: set[str] = set()
    for item in items:
        expected = f"[evidence:{item.path}]"
        if item.citation != expected:
            errors.append(f"invalid-citation:{item.path}")
        if item.citation in citations:
            errors.append(f"duplicate-citation:{item.path}")
        citations.add(item.citation)
        if len(item.content_sha256) != 64 or any(
            character not in "0123456789abcdef" for character in item.content_sha256
        ):
            errors.append(f"invalid-sha256:{item.path}")
        if not item.source_url.startswith("https://github.com/"):
            errors.append(f"invalid-source:{item.path}")
    return tuple(errors)
