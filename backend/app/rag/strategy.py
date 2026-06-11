"""Retrieval strategy definitions (Phase 6)."""

from __future__ import annotations

from enum import Enum
from pydantic import BaseModel
from app.rag.context.token_budgeter import BudgetSize


class RetrievalStrategy(str, Enum):
    FINANCIAL_METRICS = "FINANCIAL_METRICS"
    RISK_ANALYSIS = "RISK_ANALYSIS"
    TONE_ANALYSIS = "TONE_ANALYSIS"
    GUIDANCE_ANALYSIS = "GUIDANCE_ANALYSIS"
    GENERAL_ANALYSIS = "GENERAL_ANALYSIS"


class StrategyConfig(BaseModel):
    query_rewriting: bool
    hyde: bool
    retrieval_depth: int
    reranking: bool
    context_size: BudgetSize


# Configurations controlling the pipeline behavior per strategy
STRATEGY_MAP = {
    RetrievalStrategy.FINANCIAL_METRICS: StrategyConfig(
        query_rewriting=True,
        hyde=False,                 # financial metric queries prefer factual metrics over hypothetical answers
        retrieval_depth=20,
        reranking=True,
        context_size=BudgetSize.MEDIUM
    ),
    RetrievalStrategy.RISK_ANALYSIS: StrategyConfig(
        query_rewriting=True,
        hyde=True,                  # risks benefit from HyDE answering/concept expansion
        retrieval_depth=25,
        reranking=True,
        context_size=BudgetSize.LARGE
    ),
    RetrievalStrategy.TONE_ANALYSIS: StrategyConfig(
        query_rewriting=True,
        hyde=True,
        retrieval_depth=20,
        reranking=True,
        context_size=BudgetSize.MEDIUM
    ),
    RetrievalStrategy.GUIDANCE_ANALYSIS: StrategyConfig(
        query_rewriting=True,
        hyde=True,
        retrieval_depth=20,
        reranking=True,
        context_size=BudgetSize.MEDIUM
    ),
    RetrievalStrategy.GENERAL_ANALYSIS: StrategyConfig(
        query_rewriting=False,      # simple queries don't need rewritten variations
        hyde=False,
        retrieval_depth=10,
        reranking=False,
        context_size=BudgetSize.SMALL
    )
}


def get_strategy_config(strategy: RetrievalStrategy | str | None = None) -> StrategyConfig:
    """Return the configuration for a given strategy, defaulting to GENERAL."""
    if not strategy:
        return STRATEGY_MAP[RetrievalStrategy.GENERAL_ANALYSIS]

    try:
        if isinstance(strategy, str):
            strat_enum = RetrievalStrategy(strategy.upper())
        else:
            strat_enum = strategy
        return STRATEGY_MAP[strat_enum]
    except (ValueError, KeyError):
        return STRATEGY_MAP[RetrievalStrategy.GENERAL_ANALYSIS]
