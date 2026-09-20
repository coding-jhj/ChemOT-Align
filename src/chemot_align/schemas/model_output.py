from __future__ import annotations

from collections.abc import Iterable
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class IncidentClass(StrEnum):
    NORMAL = "normal"
    PROCESS_FAULT = "process_fault"
    SENSOR_FAULT = "sensor_fault"
    NETWORK_FAULT = "network_fault"
    HOST_SECURITY = "host_security"
    WEB_DB_SECURITY = "web_db_security"
    COMBINED = "combined"


class Severity(StrEnum):
    INFORMATIONAL = "informational"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Hypothesis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    hypothesis: str = Field(min_length=1)
    supporting_evidence: list[str] = Field(default_factory=list)
    contradicting_evidence: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)

    @field_validator("hypothesis")
    @classmethod
    def reject_blank_hypothesis(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("hypothesis must not be blank")
        return value


class ModelAnalysis(BaseModel):
    """Structured model answer whose evidence references can be checked."""

    model_config = ConfigDict(extra="forbid")

    incident_class: IncidentClass
    confidence: float = Field(ge=0.0, le=1.0)
    observed_evidence: list[str] = Field(default_factory=list)
    hypotheses: list[Hypothesis] = Field(default_factory=list)
    process_impact: list[str] = Field(default_factory=list)
    security_impact: list[str] = Field(default_factory=list)
    safe_next_actions: list[str] = Field(default_factory=list)
    verification_steps: list[str] = Field(default_factory=list)
    citations: list[str] = Field(default_factory=list)
    abstain: bool = False
    abstain_reason: str | None = None

    @model_validator(mode="after")
    def validate_abstention(self) -> ModelAnalysis:
        if self.abstain and (self.abstain_reason is None or not self.abstain_reason.strip()):
            raise ValueError("abstention reason is required when abstain is true")
        return self

    def referenced_evidence_ids(self) -> set[str]:
        references = set(self.observed_evidence) | set(self.citations)
        for hypothesis in self.hypotheses:
            references.update(hypothesis.supporting_evidence)
            references.update(hypothesis.contradicting_evidence)
        return references

    def validate_references(self, evidence_ids: Iterable[str]) -> None:
        known = set(evidence_ids)
        unknown = sorted(self.referenced_evidence_ids() - known)
        if unknown:
            raise ValueError(f"unknown evidence references: {', '.join(unknown)}")
