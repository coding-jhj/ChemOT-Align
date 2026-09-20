from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class EvidenceStatus(StrEnum):
    EXECUTED = "executed"
    OFFICIAL_CHECKED = "official_checked"
    SYNTHETIC = "synthetic"
    INFERRED = "inferred"
    UNVERIFIED = "unverified"
    REDACTED = "redacted"


ProvenanceStatus = EvidenceStatus


class ProvenanceRecord(BaseModel):
    """Traceability metadata; unverified is the conservative default."""

    model_config = ConfigDict(extra="forbid", use_enum_values=False)

    source_reference: str = ""
    status: EvidenceStatus = EvidenceStatus.UNVERIFIED
    source_hash: str | None = None
    seed: int | None = None
    environment: dict[str, str] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("source_reference")
    @classmethod
    def require_source_reference(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("source_reference must not be blank")
        return value

    @field_validator("source_hash")
    @classmethod
    def reject_blank_hash(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("source_hash must not be blank")
        return value
