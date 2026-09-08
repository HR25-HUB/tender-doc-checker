"""Domain contracts for immutable tender source snapshots."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SourceDocument(BaseModel):
    """One captured source document and its immutable content identity."""

    model_config = ConfigDict(frozen=True)

    relative_path: str
    size_bytes: int = Field(ge=0)
    media_type: str | None = None
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_ref: str


class TenderSourceManifest(BaseModel):
    """Manifest emitted when a source dataset is frozen."""

    model_config = ConfigDict(frozen=True)

    source: str
    external_tender_id: str
    captured_at: datetime
    documents: tuple[SourceDocument, ...]
    source_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    immutable: Literal[True] = True


class TenderSourceSnapshot(BaseModel):
    """Reference to one immutable frozen tender dataset."""

    model_config = ConfigDict(frozen=True)

    snapshot_id: UUID
    source: str
    external_tender_id: str
    captured_at: datetime
    raw_document_refs: tuple[str, ...]
    source_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    manifest_ref: str
    immutable: Literal[True] = True
