from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from ..provenance.records import ProvenanceRecord


class SimulationInputError(ValueError):
    """Raised when a simulation action cannot be accepted safely."""


class ManipulatedVariables(BaseModel):
    """Bounded control inputs accepted by the simulator."""

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    feed_flow: float = Field(ge=0.0)
    coolant_flow: float = Field(ge=0.0)
    valve_opening: float = Field(ge=0.0, le=1.0)
    pump_on: bool = True


class ProcessState(BaseModel):
    """Internal process state; invalid numeric values are never silently clamped."""

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    step: int = Field(ge=0)
    time: float = Field(ge=0.0)
    temperature: float
    pressure: float
    flow: float
    concentration: float
    level: float
    feed_flow: float = Field(ge=0.0)
    coolant_flow: float = Field(ge=0.0)
    valve_opening: float = Field(ge=0.0, le=1.0)
    pump_on: bool


class ViolationDirection(StrEnum):
    LOW = "low"
    HIGH = "high"
    NON_FINITE = "non_finite"


class SafetyViolation(BaseModel):
    """A reported bound violation, retained as data for later evidence creation."""

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    code: str = Field(min_length=1)
    variable: str = Field(min_length=1)
    value: float
    limit: float | None = None
    direction: ViolationDirection
    message: str = Field(min_length=1)


class ProcessObservation(BaseModel):
    """One simulator observation with diagnostics and provenance."""

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    step: int = Field(ge=1)
    state: ProcessState
    measurements: dict[str, float] = Field(default_factory=dict)
    alarms: list[str] = Field(default_factory=list)
    safety_violations: list[SafetyViolation] = Field(default_factory=list)
    sensor_reliability: dict[str, float] = Field(default_factory=dict)
    diagnostics: dict[str, float] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    provenance: ProvenanceRecord
