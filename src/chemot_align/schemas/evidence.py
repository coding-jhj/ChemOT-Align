from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..provenance.records import ProvenanceRecord


class SourceLayer(StrEnum):
    PROCESS = "process"
    NETWORK = "network"
    HOST = "host"
    WEB_DB = "web_db"
    IDS = "ids"
    DOCUMENT = "document"


class TrustLevel(StrEnum):
    TRUSTED = "trusted"
    LAB_OBSERVED = "lab_observed"
    SYNTHETIC = "synthetic"
    UNTRUSTED = "untrusted"


class IntegrityStatus(StrEnum):
    INTACT = "intact"
    MISSING = "missing"
    CONFLICTED = "conflicted"
    UNKNOWN = "unknown"


class Evidence(BaseModel):
    """One auditable observation or document claim in an incident case."""

    model_config = ConfigDict(extra="forbid", use_enum_values=False)

    evidence_id: str = Field(min_length=1)
    timestamp: str | None = None
    source_layer: SourceLayer
    asset_id: str = Field(min_length=1)
    event_type: str = Field(min_length=1)
    content: dict[str, Any]
    trust_level: TrustLevel
    integrity_status: IntegrityStatus
    source_reference: str = Field(min_length=1)
    is_instruction: bool = False
    provenance: ProvenanceRecord | None = None

    @field_validator("evidence_id", "asset_id", "event_type", "source_reference")
    @classmethod
    def reject_blank_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("text fields must not be blank")
        return value
