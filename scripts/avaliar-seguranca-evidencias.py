#!/usr/bin/env python3
import argparse
import json

from ai_engineering.security.evaluation import (
    EvidenceSecurityEvaluator,
    load_adversarial_cases,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Avalia controles de evidências externas")
    parser.add_argument(
        "--corpus", default="evals/evidence-security.yaml", help="Corpus YAML versionado"
    )
    parser.add_argument("--threshold", type=float, default=1.0, help="Taxa mínima de aprovação")
    args = parser.parse_args()
    report = EvidenceSecurityEvaluator(threshold=args.threshold).evaluate(
        load_adversarial_cases(args.corpus)
    )
    print(json.dumps(report.as_dict(), ensure_ascii=False, indent=2))
    return 0 if report.approved else 1


if __name__ == "__main__":
    raise SystemExit(main())
