"""HyDE implementation models."""

from __future__ import annotations

from pydantic import BaseModel, Field


class HyDEResult(BaseModel):
    query: str
    hypothetical_document: str
    metadata: dict = Field(default_factory=dict)
