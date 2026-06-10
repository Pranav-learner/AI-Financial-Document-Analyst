"""Section-aware recursive chunker (Phase 1C).

Strategy: treat each section as a logical document, recursively split it into the
smallest natural units (atoms) using a separator hierarchy, then greedily merge
atoms into chunks near the target token size (never exceeding the max), adding a
token-bounded overlap between adjacent chunks for context continuity.

Deterministic, repeatable, explainable — no AI, no embeddings.
"""

from __future__ import annotations

from app.ingestion.chunking.config import StrategyConfig
from app.ingestion.chunking.token_counter import TokenCounter, get_token_counter


class SectionChunker:
    def __init__(self, counter: TokenCounter | None = None) -> None:
        self.counter = counter or get_token_counter()

    def chunk(self, text: str, strategy: StrategyConfig) -> list[str]:
        """Split one section's text into ordered chunk strings."""
        text = text.strip()
        if not text:
            return []
        atoms = self._split_atoms(text, strategy.separators, strategy.max_tokens)
        return self._merge(atoms, strategy)

    # -- recursive atomization -------------------------------------------------

    def _split_atoms(self, text: str, separators: list[str], max_tokens: int) -> list[str]:
        """Recursively break text into pieces each <= max_tokens."""
        text = text.strip()
        if not text:
            return []
        if self.counter.count(text) <= max_tokens:
            return [text]

        sep = separators[0] if separators else ""
        rest = separators[1:] if len(separators) > 1 else [""]

        if sep == "":
            return self._hard_split(text, max_tokens)

        parts = [p for p in text.split(sep) if p.strip()]
        if len(parts) <= 1:
            # Separator didn't help; drop to the next one.
            return self._split_atoms(text, rest, max_tokens)

        atoms: list[str] = []
        for part in parts:
            if self.counter.count(part) > max_tokens:
                atoms.extend(self._split_atoms(part, rest, max_tokens))
            else:
                atoms.append(part.strip())
        return atoms

    def _hard_split(self, text: str, max_tokens: int) -> list[str]:
        """Last-resort split by words when no separator yields small-enough pieces."""
        words = text.split()
        atoms: list[str] = []
        current: list[str] = []
        for word in words:
            current.append(word)
            if self.counter.count(" ".join(current)) >= max_tokens:
                atoms.append(" ".join(current))
                current = []
        if current:
            atoms.append(" ".join(current))
        return atoms

    # -- merge into target-sized chunks with overlap ---------------------------

    def _merge(self, atoms: list[str], strategy: StrategyConfig) -> list[str]:
        chunks: list[str] = []
        current: list[str] = []
        current_tokens = 0

        for atom in atoms:
            atom_tokens = self.counter.count(atom)
            if current and current_tokens + atom_tokens > strategy.target_tokens:
                chunks.append("\n\n".join(current))
                current, current_tokens = self._overlap_tail(current, strategy)
            current.append(atom)
            current_tokens += atom_tokens

        if current:
            chunks.append("\n\n".join(current))
        return [c for c in (c.strip() for c in chunks) if c]

    def _overlap_tail(
        self, atoms: list[str], strategy: StrategyConfig
    ) -> tuple[list[str], int]:
        """Return trailing atoms (~overlap_tokens) to prepend to the next chunk."""
        if strategy.overlap_tokens <= 0:
            return [], 0
        tail: list[str] = []
        tokens = 0
        for atom in reversed(atoms):
            atom_tokens = self.counter.count(atom)
            if tail and tokens + atom_tokens > strategy.overlap_tokens:
                break
            tail.insert(0, atom)
            tokens += atom_tokens
            if tokens >= strategy.overlap_tokens:
                break
        # Never let overlap dominate a chunk.
        if tokens > strategy.target_tokens:
            return [], 0
        return tail, tokens
