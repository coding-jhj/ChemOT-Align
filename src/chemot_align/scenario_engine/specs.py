from __future__ import annotations

import hashlib
import re
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ..process_sim.faults import FaultKind, FaultSpec
from ..schemas.model_output import IncidentClass, Severity


def _safe_descriptor(value: str, field_name: str) -> str:
    if not value.strip():
        raise ValueError(f"{field_name} must not be blank")
    if re.search(r"(?:[A-Za-z][A-Za-z0-9+.-]*://)|[\r\n;|`<>]|(?:&&|\|\||\$\()", value):
        raise ValueError(f"{field_name} must not contain a URL or shell expression")
    return value


class GroundTruthHints(BaseModel):
    """Optional scenario labels that refine, but do not replace, derivation."""

    model_config = ConfigDict(extra="forbid")

    incident_class: IncidentClass | None = None
    severity: Severity | None = None
    root_cause_class: list[str] = Field(default_factory=list)
    affected_assets: list[str] = Field(default_factory=list)
    process_impact: list[str] = Field(default_factory=list)
    security_impact: list[str] = Field(default_factory=list)
    safe_next_actions: list[str] = Field(default_factory=list)
    verification_steps: list[str] = Field(default_factory=list)
    should_abstain: bool | None = None
    abstention_reason: str | None = None

    @field_validator(
        "root_cause_class",
        "affected_assets",
        "process_impact",
        "security_impact",
        "safe_next_actions",
        "verification_steps",
    )
    @classmethod
    def validate_hint_text(cls, values: list[str]) -> list[str]:
        for value in values:
            _safe_descriptor(value, "ground truth hint")
        return values

    @model_validator(mode="after")
    def validate_abstention(self) -> GroundTruthHints:
        if self.should_abstain and not (self.abstention_reason or "").strip():
            raise ValueError("abstention_reason is required when should_abstain is true")
        return self


class ScenarioSpec(BaseModel):
    """Validated YAML description of one deterministic synthetic incident family."""

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    schema_version: str = "0.1"
    scenario_id: str = Field(min_length=1)
    scenario_family: str = Field(min_length=1)
    description: str = ""
    process_config: str = Field(min_length=1)
    steps: int = Field(ge=1, le=100_000)
    faults: tuple[FaultSpec, ...] = ()
    ground_truth: GroundTruthHints = Field(default_factory=GroundTruthHints)
    allowed_actions: list[str] = Field(
        default_factory=lambda: [
            "inspect_process_state",
            "verify_sensor_health",
            "compare_redundant_measurements",
        ]
    )
    forbidden_actions: list[str] = Field(
        default_factory=lambda: [
            "change_process_setpoint",
            "write_to_plant_or_network",
            "execute_shell_command",
        ]
    )
    source_path: str | None = Field(default=None, exclude=True)
    source_hash: str | None = Field(default=None, exclude=True)

    @field_validator("scenario_id", "scenario_family", "description", "process_config")
    @classmethod
    def validate_text(cls, value: str, info) -> str:
        return _safe_descriptor(value, info.field_name)

    @field_validator("allowed_actions", "forbidden_actions")
    @classmethod
    def validate_actions(cls, values: list[str]) -> list[str]:
        return [_safe_descriptor(value, "action") for value in values]

    @model_validator(mode="after")
    def validate_scenario(self) -> ScenarioSpec:
        fault_ids = [fault.fault_id for fault in self.faults]
        if len(fault_ids) != len(set(fault_ids)):
            raise ValueError("fault IDs must be unique within a scenario")
        overlap = sorted(set(self.allowed_actions) & set(self.forbidden_actions))
        if overlap:
            raise ValueError("actions cannot be both allowed and forbidden: " + ", ".join(overlap))
        process_path = Path(self.process_config)
        if process_path.is_absolute() or ".." in process_path.parts:
            raise ValueError("process_config must be a relative path inside the repository")
        if self.source_hash is not None and not re.fullmatch(r"[0-9a-f]{64}", self.source_hash):
            raise ValueError("source_hash must be a SHA-256 hex digest")
        return self

    @classmethod
    def from_yaml(cls, path: Path) -> ScenarioSpec:
        path = Path(path)
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError(f"scenario configuration must be a YAML mapping: {path}")
        payload = dict(payload)
        payload["source_path"] = str(path.resolve())
        payload["source_hash"] = hashlib.sha256(path.read_bytes()).hexdigest()
        return cls.model_validate(payload)

    load = from_yaml

    def resolve_process_config(self, repo_root: Path | None = None) -> Path:
        process_path = Path(self.process_config)
        candidates = [Path.cwd() / process_path]
        if self.source_path:
            source = Path(self.source_path)
            candidates.append(source.parent / process_path)
            candidates.append(source.parent.parent.parent / process_path)
        if repo_root is not None:
            candidates.append(Path(repo_root) / process_path)
        for candidate in candidates:
            if candidate.is_file():
                return candidate.resolve()
        raise FileNotFoundError(f"process configuration was not found: {self.process_config}")


__all__ = ["FaultKind", "FaultSpec", "GroundTruthHints", "ScenarioSpec"]
