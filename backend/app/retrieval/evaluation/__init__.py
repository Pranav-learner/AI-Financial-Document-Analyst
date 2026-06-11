"""Retrieval evaluation & observability (Phase 2D).

Measure retrieval quality objectively with a reusable benchmark suite + metrics
(Recall@K, Precision@K, MRR, Hit Rate, latency, candidate reduction). Strategy-
agnostic so vector, hybrid, and any future strategy are scored identically and
compared. **Measurement only** — no retrieval enhancement, no LLM judge, no RAG.

Public surface:

    from app.retrieval.evaluation import (
        EvaluationService, get_store, BenchmarkRunner,
        get_ground_truth, load_ground_truth,
    )
"""

from app.retrieval.evaluation.benchmark_runner import BenchmarkRunner, RetrievalOutput
from app.retrieval.evaluation.evaluation_exceptions import (
    EvaluationError,
    GroundTruthError,
    InvalidEvaluationRequestError,
    UnknownBenchmarkError,
)
from app.retrieval.evaluation.evaluation_models import EvaluationResult, EvaluationRun
from app.retrieval.evaluation.evaluation_service import (
    VALID_TYPES,
    EvaluationService,
    EvaluationStore,
    get_store,
)
from app.retrieval.evaluation.ground_truth import (
    GroundTruthExample,
    get_ground_truth,
    load_ground_truth,
)

__all__ = [
    "EvaluationService",
    "EvaluationStore",
    "get_store",
    "VALID_TYPES",
    "BenchmarkRunner",
    "RetrievalOutput",
    "EvaluationResult",
    "EvaluationRun",
    "GroundTruthExample",
    "get_ground_truth",
    "load_ground_truth",
    "EvaluationError",
    "GroundTruthError",
    "UnknownBenchmarkError",
    "InvalidEvaluationRequestError",
]
