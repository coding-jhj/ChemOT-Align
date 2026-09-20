from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ProcessState(BaseModel):
    """Typed process state shared with the future simulator implementation."""

    model_config = ConfigDict(extra="forbid")

    temperature: float
    pressure: float
    flow: float
    concentration: float
    level: float | None = None


class ProcessObservation(BaseModel):
    """A process state plus observed measurements and alarms."""

    model_config = ConfigDict(extra="forbid")

    timestamp: str | None = None
    asset_id: str = Field(min_length=1)
    state: ProcessState
    measurements: dict[str, float] = Field(default_factory=dict)
    alarms: list[str] = Field(default_factory=list)
    sensor_reliability: dict[str, float] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
