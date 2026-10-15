from pathlib import Path

import pytest

from ai_engineering.evidence.models import EvidenceContextItem
from ai_engineering.security.evaluation import (
    AdversarialCase,
    EvidenceSecurityEvaluator,
    load_adversarial_cases,
    validate_evidence_context,
)

CORPUS = Path(__file__).parents[2] / "evals" / "evidence-security.yaml"


def test_versioned_adversarial_corpus_meets_full_threshold() -> None:
    report = EvidenceSecurityEvaluator(threshold=1.0).evaluate(
        load_adversarial_cases(CORPUS)
    )

    assert report.approved is True
    assert report.total == 10
    assert report.passed == report.total
    assert report.failed == 0
    assert report.categories["prompt-injection"] == {"total": 5, "passed": 5}
    assert report.categories["secret-redaction"] == {"total": 3, "passed": 3}


def test_evaluator_reports_a_regression_without_hiding_it() -> None:
    report = EvidenceSecurityEvaluator().evaluate(
        [
            AdversarialCase(
                id="incorrect-expectation",
                category="regression",
                content="Texto benigno.",
                expected_status="quarantined",
            )
        ]
    )

    assert report.approved is False
    assert report.failed == 1
    assert report.results[0].actual_status == "included"


def test_evaluator_rejects_empty_or_invalid_corpus() -> None:
    evaluator = EvidenceSecurityEvaluator()
    with pytest.raises(ValueError, match="não pode ser vazio"):
        evaluator.evaluate([])
    with pytest.raises(ValueError, match="Status esperado inválido"):
        evaluator.evaluate(
            [AdversarialCase("invalid", "invalid", "texto", "unknown")]
        )


def test_context_validator_detects_tampered_citations_and_budget() -> None:
    item = EvidenceContextItem(
        citation="[evidence:other.md]",
        path="README.md",
        source_url="https://example.invalid/README.md",
        content_sha256="not-a-hash",
        content="0123456789",
    )

    errors = validate_evidence_context([item], max_chars=5)

    assert "context-budget-exceeded" in errors
    assert "invalid-citation:README.md" in errors
    assert "invalid-sha256:README.md" in errors
    assert "invalid-source:README.md" in errors
