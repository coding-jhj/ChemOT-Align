from __future__ import annotations

import pytest
from pydantic import ValidationError

from chemot_align.provenance.records import ProvenanceRecord
from chemot_align.schemas.evidence import Evidence


def make_evidence(**overrides: object) -> Evidence:
    payload: dict[str, object] = {
        "evidence_id": "ev-001",
        "timestamp": None,
        "source_layer": "process",
        "asset_id": "reactor-01",
        "event_type": "metric",
        "content": {"temperature": 300.0},
        "trust_level": "synthetic",
        "integrity_status": "intact",
        "source_reference": "fixture://process/case-001",
    }
    payload.update(overrides)
    return Evidence(**payload)


def test_evidence_requires_a_non_empty_id() -> None:
    with pytest.raises(ValidationError):
        make_evidence(evidence_id="")


def test_evidence_rejects_unknown_source_layer() -> None:
    with pytest.raises(ValidationError):
        make_evidence(source_layer="unknown-layer")


def test_evidence_requires_a_source_reference() -> None:
    with pytest.raises(ValidationError):
        make_evidence(source_reference="")


def test_evidence_accepts_provenance_record() -> None:
    provenance = ProvenanceRecord(source_reference="fixture://process/case-001", status="synthetic")

    evidence = make_evidence(provenance=provenance)

    assert evidence.provenance.status.value == "synthetic"
