from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ..provenance.records import ProvenanceRecord
from .evidence import Evidence
from .model_output import Hypothesis, IncidentClass, ModelAnalysis, Severity


class GroundTruth(BaseModel):
    model_config = ConfigDict(extra="forbid")

    incident_class: IncidentClass
    severity: Severity
    root_cause_class: list[str] = Field(default_factory=list)
    affected_assets: list[str] = Field(default_factory=list)
    required_evidence: list[str] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    process_impact: list[str] = Field(default_factory=list)
    security_impact: list[str] = Field(default_factory=list)
    safe_next_actions: list[str] = Field(default_factory=list)
    verification_steps: list[str] = Field(default_factory=list)
    should_abstain: bool = False
    abstention_reason: str | None = None

    @model_validator(mode="after")
    def validate_abstention(self) -> GroundTruth:
        if self.should_abstain and (
            self.abstention_reason is None or not self.abstention_reason.strip()
        ):
            raise ValueError("abstention reason is required when should_abstain is true")
        return self


class IncidentCase(BaseModel):
    """Common case contract for process, Lab, RAG, and evaluation stages."""

    model_config = ConfigDict(extra="forbid")

    case_id: str = Field(min_length=1)
    scenario_family: str = Field(min_length=1)
    seed: int
    evidence: list[Evidence]
    ground_truth: GroundTruth
    allowed_actions: list[str]
    forbidden_actions: list[str]
    provenance: ProvenanceRecord
    model_analysis: ModelAnalysis | None = None

    @field_validator("case_id", "scenario_family")
    @classmethod
    def reject_blank_identity(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("case identity fields must not be blank")
        return value

    @model_validator(mode="after")
    def validate_cross_field_contract(self) -> IncidentCase:
        evidence_ids = [item.evidence_id for item in self.evidence]
        duplicate_ids = sorted({item for item in evidence_ids if evidence_ids.count(item) > 1})
        if duplicate_ids:
            raise ValueError(f"duplicate evidence IDs: {', '.join(duplicate_ids)}")

        overlapping_actions = sorted(set(self.allowed_actions) & set(self.forbidden_actions))
        if overlapping_actions:
            raise ValueError(
                "actions cannot be both allowed and forbidden: "
                + ", ".join(overlapping_actions)
            )

        if self.model_analysis is not None:
            self.model_analysis.validate_references(evidence_ids)
        return self


__all__ = [
    "GroundTruth",
    "Hypothesis",
    "IncidentCase",
    "IncidentClass",
    "ModelAnalysis",
    "Severity",
]
