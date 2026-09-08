"""Application service for TOF-001.0 tender source freezing."""

from __future__ import annotations

import hashlib
import json
import mimetypes
import shutil
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from src.tender_opportunity.domain.source_snapshot import (
    SourceDocument,
    TenderSourceManifest,
    TenderSourceSnapshot,
)


class EmptyTenderSourceError(ValueError):
    """Raised when the selected tender source contains no files."""


class SnapshotVerificationError(ValueError):
    """Raised when a frozen snapshot no longer matches its manifest."""


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _aggregate_source_hash(documents: tuple[SourceDocument, ...]) -> str:
    """Hash only deterministic content identity, excluding capture metadata."""
    payload = [
        {
            "relative_path": item.relative_path,
            "sha256": item.sha256,
            "size_bytes": item.size_bytes,
        }
        for item in sorted(documents, key=lambda value: value.relative_path)
    ]
    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def freeze_tender_source(
    *,
    source_dir: Path,
    snapshot_dir: Path,
    source: str,
    external_tender_id: str,
    captured_at: datetime | None = None,
) -> TenderSourceSnapshot:
    """Freeze one source directory and produce a deterministic manifest."""
    source_dir = source_dir.resolve()
    snapshot_dir = snapshot_dir.resolve()

    input_files = tuple(
        sorted(
            (path for path in source_dir.rglob("*") if path.is_file()),
            key=lambda path: path.relative_to(source_dir).as_posix(),
        )
    )
    if not input_files:
        raise EmptyTenderSourceError(f"No tender source files found in {source_dir}")

    captured = captured_at or datetime.now(UTC)
    documents: list[SourceDocument] = []
    raw_refs: list[str] = []

    for input_path in input_files:
        relative = input_path.relative_to(source_dir)
        output_path = snapshot_dir / "source" / relative
        output_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(input_path, output_path)

        ref = (Path("source") / relative).as_posix()
        media_type, _ = mimetypes.guess_type(input_path.name)
        document = SourceDocument(
            relative_path=relative.as_posix(),
            size_bytes=output_path.stat().st_size,
            media_type=media_type,
            sha256=_sha256_file(output_path),
            source_ref=ref,
        )
        documents.append(document)
        raw_refs.append(ref)

    frozen_documents = tuple(documents)
    source_hash = _aggregate_source_hash(frozen_documents)
    manifest = TenderSourceManifest(
        source=source,
        external_tender_id=external_tender_id,
        captured_at=captured,
        documents=frozen_documents,
        source_hash=source_hash,
    )

    snapshot_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = snapshot_dir / "manifest.json"
    manifest_path.write_text(
        manifest.model_dump_json(indent=2),
        encoding="utf-8",
    )

    return TenderSourceSnapshot(
        snapshot_id=uuid4(),
        source=source,
        external_tender_id=external_tender_id,
        captured_at=captured,
        raw_document_refs=tuple(raw_refs),
        source_hash=source_hash,
        manifest_ref="manifest.json",
    )


def verify_tender_snapshot(snapshot_dir: Path) -> TenderSourceManifest:
    """Verify every frozen file and the aggregate source hash."""
    snapshot_dir = snapshot_dir.resolve()
    manifest_path = snapshot_dir / "manifest.json"
    manifest = TenderSourceManifest.model_validate_json(
        manifest_path.read_text(encoding="utf-8")
    )

    verified_documents: list[SourceDocument] = []
    for expected in manifest.documents:
        path = snapshot_dir / expected.source_ref
        if not path.is_file():
            raise SnapshotVerificationError(
                f"Missing frozen tender file: {expected.relative_path}"
            )
        actual_hash = _sha256_file(path)
        actual_size = path.stat().st_size
        if actual_hash != expected.sha256 or actual_size != expected.size_bytes:
            raise SnapshotVerificationError(
                f"Tender source mutation detected: {expected.relative_path}"
            )
        verified_documents.append(expected)

    actual_source_hash = _aggregate_source_hash(tuple(verified_documents))
    if actual_source_hash != manifest.source_hash:
        raise SnapshotVerificationError("Aggregate tender source hash mismatch")

    return manifest
