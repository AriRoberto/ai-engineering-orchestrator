from ai_engineering.evidence.models import EvidenceCollection, EvidenceContextItem


class EvidenceContextBuilder:
    def __init__(self, max_chars: int = 12_000) -> None:
        if max_chars < 1:
            raise ValueError("O orçamento de contexto deve ser positivo")
        self.max_chars = max_chars

    def build(self, collection: EvidenceCollection) -> list[EvidenceContextItem]:
        context: list[EvidenceContextItem] = []
        remaining = self.max_chars
        for item in collection.files:
            if item.content_status not in {"included", "redacted"} or not item.content:
                continue
            if remaining <= 0:
                break
            content = item.content[:remaining]
            context.append(
                EvidenceContextItem(
                    citation=f"[evidence:{item.path}]",
                    path=item.path,
                    source_url=item.source_url,
                    content_sha256=item.content_sha256 or "",
                    content=content,
                    truncated=len(content) < len(item.content),
                )
            )
            remaining -= len(content)
        return context
