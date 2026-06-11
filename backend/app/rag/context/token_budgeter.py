"""Token budget management (Phase 6)."""

from __future__ import annotations

from enum import Enum
from app.core.logging import get_logger
from app.ingestion.chunking.token_counter import get_token_counter

log = get_logger(__name__)


class BudgetSize(str, Enum):
    SMALL = "SMALL"       # 4,000 tokens
    MEDIUM = "MEDIUM"     # 16,000 tokens
    LARGE = "LARGE"       # 64,000 tokens


BUDGET_LIMITS = {
    BudgetSize.SMALL: 4000,
    BudgetSize.MEDIUM: 16000,
    BudgetSize.LARGE: 64000
}


class TokenBudgeter:
    """Manages token allocation and prevents context overflow."""

    def __init__(self, size: BudgetSize | str = BudgetSize.SMALL) -> None:
        if isinstance(size, str):
            try:
                self.size = BudgetSize(size.upper())
            except ValueError:
                self.size = BudgetSize.SMALL
        else:
            self.size = size

        self.limit = BUDGET_LIMITS[self.size]
        self.counter = get_token_counter()

    def count_tokens(self, text: str) -> int:
        return self.counter.count(text)

    def fit_chunks(self, chunks: list) -> list:
        """Select a subset of chunks that fit within the token budget.

        Since candidates are already ranked by relevance/confidence, we iterate in order,
        adding chunks until the budget limit is reached.
        """
        admitted = []
        cumulative_tokens = 0

        for ch in chunks:
            # Check if chunk has text attribute or chunk_text
            text = getattr(ch, "chunk_text", getattr(ch, "text", ""))
            tokens = self.count_tokens(text)

            if cumulative_tokens + tokens <= self.limit:
                admitted.append(ch)
                cumulative_tokens += tokens
            else:
                log.info(
                    "token_budget.reached",
                    limit=self.limit,
                    cumulative=cumulative_tokens,
                    next_chunk_tokens=tokens
                )
                break

        return admitted
