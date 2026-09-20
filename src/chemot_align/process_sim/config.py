from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from .state import ManipulatedVariables, ProcessState


class SafetyBounds(BaseModel):
    """Configured educational bounds; crossing a bound emits evidence."""

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    temperature_min: float = 250.0
    temperature_max: float = 450.0
    pressure_min: float = 0.0
    pressure_max: float = 10.0
    flow_min: float = 0.0
    flow_max: float = 2.0
    concentration_min: float = 0.0
    concentration_max: float = 2.0
    level_min: float = 0.0
    level_max: float = 1.0

    @model_validator(mode="after")
    def validate_ordering(self) -> SafetyBounds:
        pairs = (
            ("temperature", self.temperature_min, self.temperature_max),
            ("pressure", self.pressure_min, self.pressure_max),
            ("flow", self.flow_min, self.flow_max),
            ("concentration", self.concentration_min, self.concentration_max),
            ("level", self.level_min, self.level_max),
        )
        for name, lower, upper in pairs:
            if lower >= upper:
                raise ValueError(f"{name} safety lower bound must be less than upper bound")
        return self


class CSTRConfig(BaseModel):
    """Constant-volume CSTR parameters loaded from a versioned YAML file."""

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    name: str = Field(min_length=1)
    dt: float = Field(gt=0.0)
    volume: float = Field(gt=0.0)
    density: float = Field(gt=0.0)
    heat_capacity: float = Field(gt=0.0)
    reaction_heat: float
    rate_constant_reference: float = Field(ge=0.0)
    reference_temperature: float = Field(gt=0.0)
    activation_energy: float = Field(ge=0.0)
    gas_constant: float = Field(gt=0.0)
    max_rate_constant: float = Field(gt=0.0)
    feed_concentration: float = Field(ge=0.0)
    feed_temperature: float
    nominal_outflow: float = Field(ge=0.0)
    coolant_heat_transfer: float = Field(ge=0.0)
    pressure_relaxation: float = Field(ge=0.0)
    pressure_flow_gain: float = Field(ge=0.0)
    measurement_noise_std: float = Field(ge=0.0)
    max_feed_flow: float = Field(gt=0.0)
    max_coolant_flow: float = Field(gt=0.0)
    initial_temperature: float
    initial_pressure: float
    initial_flow: float = Field(ge=0.0)
    initial_concentration: float = Field(ge=0.0)
    initial_level: float = Field(ge=0.0)
    initial_pump_on: bool = True
    initial_valve_opening: float = Field(ge=0.0, le=1.0)
    default_action: ManipulatedVariables
    bounds: SafetyBounds

    @classmethod
    def from_yaml(cls, path: Path) -> CSTRConfig:
        path = Path(path)
        try:
            payload: Any = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            raise ValueError(f"invalid process YAML: {path}") from exc
        if not isinstance(payload, dict):
            raise ValueError(f"process configuration must be a YAML mapping: {path}")
        return cls.model_validate(payload)

    def initial_state(self) -> ProcessState:
        return ProcessState(
            step=0,
            time=0.0,
            temperature=self.initial_temperature,
            pressure=self.initial_pressure,
            flow=self.initial_flow,
            concentration=self.initial_concentration,
            level=self.initial_level,
            feed_flow=self.default_action.feed_flow,
            coolant_flow=self.default_action.coolant_flow,
            valve_opening=self.initial_valve_opening,
            pump_on=self.initial_pump_on,
        )


ProcessConfig = CSTRConfig
