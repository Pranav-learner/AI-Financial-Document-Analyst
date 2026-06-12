"""API v1 aggregate router.

Mounts all v1 sub-routers. Today only operational endpoints exist. Business
routers (upload, search, metrics, risks, benchmark, memos, chat, export — see
docs/04_API_DESIGN.md) are added in their respective phases and included here.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import RoleChecker
from app.api.v1.endpoints import (
    analytics,
    auth,
    benchmark,
    chunks,
    comparisons,
    embeddings,
    evaluation,
    health,
    memo,
    metrics,
    rag,
    reports,
    risks,
    search,
    tone,
    agent,
)
from app.models.enums import UserRole

api_router = APIRouter()

# Authentication endpoints (Phase 11).
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])

# Operational endpoints (Phase 0.5) - Open/Public.
api_router.include_router(health.router)

# Report ingestion + sections + chunks (Phase 1A/1B/1C).
api_router.include_router(reports.router, prefix="/reports", tags=["reports"], dependencies=[Depends(RoleChecker(UserRole.VIEWER))])
api_router.include_router(chunks.router, prefix="/chunks", tags=["chunks"], dependencies=[Depends(RoleChecker(UserRole.VIEWER))])

# Embedding generation + operational monitoring (Phase 2A). Report-scoped paths.
api_router.include_router(embeddings.router, prefix="/reports", tags=["embeddings"], dependencies=[Depends(RoleChecker(UserRole.VIEWER))])

# Vector + hybrid search (Phase 2B/2C) — retrieval only, no reasoning.
api_router.include_router(search.router, prefix="/search", tags=["search"], dependencies=[Depends(RoleChecker(UserRole.VIEWER))])

# Retrieval evaluation & observability (Phase 2D) — measurement only.
api_router.include_router(evaluation.router, prefix="/evaluation", tags=["evaluation"], dependencies=[Depends(RoleChecker(UserRole.VIEWER))])

# Financial metric extraction (Phase 3A) — report-scoped; inspection + trigger.
api_router.include_router(metrics.router, prefix="/reports", tags=["metrics"], dependencies=[Depends(RoleChecker(UserRole.VIEWER))])

# Period comparisons (Phase 3B) — report + company scoped; full paths inside.
api_router.include_router(comparisons.router, tags=["comparisons"], dependencies=[Depends(RoleChecker(UserRole.VIEWER))])

# Financial analytics (Phase 3C) — report + company scoped; full paths inside.
api_router.include_router(analytics.router, tags=["analytics"], dependencies=[Depends(RoleChecker(UserRole.VIEWER))])

# Risk intelligence (Phase 4) — report + company scoped; full paths inside.
api_router.include_router(risks.router, tags=["risks"], dependencies=[Depends(RoleChecker(UserRole.VIEWER))])

# Management tone intelligence (Phase 5) — report + company scoped; full paths inside.
api_router.include_router(tone.router, tags=["tone"], dependencies=[Depends(RoleChecker(UserRole.VIEWER))])

# Advanced Retrieval & RAG (Phase 6)
api_router.include_router(rag.router, prefix="/rag", tags=["rag"], dependencies=[Depends(RoleChecker(UserRole.VIEWER))])

# Financial Analyst Agent System (Phase 7)
api_router.include_router(agent.router, prefix="/agent", tags=["agent"], dependencies=[Depends(RoleChecker(UserRole.VIEWER))])

# --- Business routers (added per phase) ---------------------------------------
api_router.include_router(benchmark.router, prefix="/benchmark", tags=["benchmark"], dependencies=[Depends(RoleChecker(UserRole.VIEWER))])
api_router.include_router(memo.router,     prefix="/memos",     tags=["memos"], dependencies=[Depends(RoleChecker(UserRole.VIEWER))])      # Phase 9
# api_router.include_router(chat.router,      prefix="/chat",      tags=["chat"])       # Phase 10
