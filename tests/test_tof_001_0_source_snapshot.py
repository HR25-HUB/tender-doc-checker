"""Executable acceptance tests for TOF-001.0."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from src.tender_opportunity.application.freeze_tender_source import (
    SnapshotVerificationError,
    freeze_tender_source,
    verify_tender_snapshot,
)


def _write_source_dataset(root: Path) -> None:
    (root / "docs").mkdir(parents=True)
    (root / "notice.txt").write_text("Tender notice v1\n", encoding="utf-8")
    (root / "docs" / "specification.csv").write_text(
        "item,qty\nABB S203-C16,10\n",
        encoding="utf-8",
    )


def test_freeze_accounts_for_every_source_file(tmp_path: Path) -> None:
    source_dir = tmp_path / "input"
    snapshot_dir = tmp_path / "snapshot"
    _write_source_dataset(source_dir)

    snapshot = freeze_tender_source(
        source_dir=source_dir,
        snapshot_dir=snapshot_dir,
        source="golden-test",
        external_tender_id="TENDER-001",
        captured_at=datetime(2026, 9, 8, 18, 0, tzinfo=UTC),
    )
    manifest = verify_tender_snapshot(snapshot_dir)

    assert snapshot.immutable is True
    assert {doc.relative_path for doc in manifest.documents} == {
        "docs/specification.csv",
        "notice.txt",
    }
    assert len(snapshot.raw_document_refs) == 2


def test_same_input_produces_same_hashes(tmp_path: Path) -> None:
    source_dir = tmp_path / "input"
    _write_source_dataset(source_dir)

    first = freeze_tender_source(
        source_dir=source_dir,
        snapshot_dir=tmp_path / "snapshot-a",
        source="golden-test",
        external_tender_id="TENDER-001",
    )
    second = freeze_tender_source(
        source_dir=source_dir,
        snapshot_dir=tmp_path / "snapshot-b",
        source="golden-test",
        external_tender_id="TENDER-001",
    )

    first_manifest = verify_tender_snapshot(tmp_path / "snapshot-a")
    second_manifest = verify_tender_snapshot(tmp_path / "snapshot-b")

    assert first.source_hash == second.source_hash
    assert [doc.sha256 for doc in first_manifest.documents] == [
        doc.sha256 for doc in second_manifest.documents
    ]


def test_mutation_is_detected(tmp_path: Path) -> None:
    source_dir = tmp_path / "input"
    snapshot_dir = tmp_path / "snapshot"
    _write_source_dataset(source_dir)

    freeze_tender_source(
        source_dir=source_dir,
        snapshot_dir=snapshot_dir,
        source="golden-test",
        external_tender_id="TENDER-001",
    )

    (snapshot_dir / "source" / "notice.txt").write_text(
        "mutated after freeze\n",
        encoding="utf-8",
    )

    with pytest.raises(
        SnapshotVerificationError,
        match="Tender source mutation detected: notice.txt",
    ):
        verify_tender_snapshot(snapshot_dir)
