from __future__ import annotations

import pytest
from pydantic import ValidationError

from chemot_align.provenance.records import ProvenanceRecord
from chemot_align.schemas.evidence import Evidence
from chemot_align.schemas.incident import (
    GroundTruth,
    IncidentCase,
    IncidentClass,
    ModelAnalysis,
    Severity,
)


def make_evidence(evidence_id: str) -> Evidence:
    return Evidence(
        evidence_id=evidence_id,
        timestamp=None,
        source_layer="process",
        asset_id="reactor-01",
        event_type="metric",
        content={"temperature": 300.0},
        trust_level="synthetic",
        integrity_status="intact",
        source_reference="fixture://process/case-001",
    )


def make_ground_truth() -> GroundTruth:
    return GroundTruth(
        incident_class=IncidentClass.PROCESS_FAULT,
        severity=Severity.MEDIUM,
    )


def make_provenance() -> ProvenanceRecord:
    return ProvenanceRecord(
        source_reference="fixture://incident/case-001",
        status="synthetic",
        seed=1,
    )


def make_case(
    evidence: list[Evidence], model_analysis: ModelAnalysis | None = None
) -> IncidentCase:
    return IncidentCase(
        case_id="case-001",
        scenario_family="process_fault",
        seed=1,
        evidence=evidence,
        ground_truth=make_ground_truth(),
        allowed_actions=["inspect_state"],
        forbidden_actions=["change_control"],
        provenance=make_provenance(),
        model_analysis=model_analysis,
    )


def test_incident_rejects_duplicate_evidence_ids() -> None:
    with pytest.raises(ValueError, match="duplicate evidence"):
        make_case([make_evidence("ev-001"), make_evidence("ev-001")])


def test_model_output_rejects_unknown_evidence_reference() -> None:
    analysis = ModelAnalysis(
        incident_class=IncidentClass.PROCESS_FAULT,
        confidence=0.5,
        observed_evidence=["ev-404"],
    )

    with pytest.raises(ValueError, match="unknown evidence"):
        make_case([make_evidence("ev-001")], analysis)


def test_model_output_rejects_confidence_outside_zero_one() -> None:
    with pytest.raises(ValidationError):
        ModelAnalysis(
            incident_class=IncidentClass.PROCESS_FAULT,
            confidence=1.1,
        )


def test_abstention_requires_a_reason() -> None:
    with pytest.raises(ValueError, match="abstention reason"):
        ModelAnalysis(
            incident_class=IncidentClass.COMBINED,
            confidence=0.2,
            abstain=True,
        )


def test_model_output_accepts_known_evidence_references() -> None:
    analysis = ModelAnalysis(
        incident_class=IncidentClass.PROCESS_FAULT,
        confidence=0.5,
        observed_evidence=["ev-001"],
        citations=["ev-001"],
    )

    case = make_case([make_evidence("ev-001")], analysis)

    assert case.model_analysis is analysis
