from __future__ import annotations

import hashlib
import re
from enum import StrEnum
from typing import Any

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    PrivateAttr,
    field_validator,
    model_validator,
)

from .state import ManipulatedVariables, ProcessObservation


class FaultKind(StrEnum):
    """Supported bounded fault families for synthetic process cases."""

    SENSOR_DRIFT = "sensor_drift"
    SENSOR_DROPOUT = "sensor_dropout"
    VALVE_DELAY = "valve_delay"
    COOLING_LOSS = "cooling_loss"
    MISSING_EVIDENCE = "missing_evidence"


FaultType = FaultKind

_UNSAFE_TEXT = re.compile(r"(?:[A-Za-z][A-Za-z0-9+.-]*://)|[\r\n;|`<>]|(?:&&|\|\||\$\()")


class FaultSpec(BaseModel):
    """A validated, deterministic fault injection specification.

    Faults can alter bounded process controls or observations only during their
    configured step window. They never execute commands, open URLs, or accept
    unbounded numeric parameters.
    """

    model_config = ConfigDict(
        extra="forbid",
        allow_inf_nan=False,
        populate_by_name=True,
    )

    fault_id: str = Field(min_length=1)
    fault_type: FaultKind = Field(
        validation_alias=AliasChoices("fault_type", "kind", "fault_kind")
    )
    start_step: int = Field(ge=1)
    duration: int = Field(ge=1, le=10_000)
    target_asset: str = Field(min_length=1)
    parameters: dict[str, float] = Field(default_factory=dict)
    label: str = Field(min_length=1)

    _action_history: list[ManipulatedVariables] = PrivateAttr(default_factory=list)

    @property
    def kind(self) -> FaultKind:
        """Compatibility alias for callers that use ``kind`` terminology."""

        return self.fault_type

    @field_validator("fault_id", "target_asset", "label")
    @classmethod
    def validate_safe_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("fault text fields must not be blank")
        if _UNSAFE_TEXT.search(value):
            raise ValueError("fault text must not contain a URL or shell expression")
        return value

    @field_validator("parameters")
    @classmethod
    def validate_parameter_names(cls, value: dict[str, float]) -> dict[str, float]:
        for name in value:
            if not re.fullmatch(r"[a-z][a-z0-9_]*", name):
                raise ValueError(f"invalid fault parameter name: {name}")
        return value

    @model_validator(mode="after")
    def validate_parameters(self) -> FaultSpec:
        allowed = {
            FaultKind.SENSOR_DRIFT: {"drift_per_step", "rate", "magnitude", "max_offset"},
            FaultKind.SENSOR_DROPOUT: {"dropout_probability", "probability"},
            FaultKind.VALVE_DELAY: {"delay_steps"},
            FaultKind.COOLING_LOSS: {"loss_fraction", "remaining_fraction"},
            FaultKind.MISSING_EVIDENCE: {"dropout_probability", "probability"},
        }[self.fault_type]
        unknown = sorted(set(self.parameters) - allowed)
        if unknown:
            raise ValueError(
                f"unsupported parameters for {self.fault_type.value}: {', '.join(unknown)}"
            )

        if self.fault_type is FaultKind.SENSOR_DRIFT:
            rate = self.parameter("drift_per_step", "rate", "magnitude", default=0.0)
            max_offset = self.parameter("max_offset", default=100.0)
            if abs(rate) > 10.0:
                raise ValueError("sensor drift rate must be between -10 and 10")
            if not 0.0 <= max_offset <= 100.0:
                raise ValueError("sensor drift max_offset must be between 0 and 100")
        elif self.fault_type in {FaultKind.SENSOR_DROPOUT, FaultKind.MISSING_EVIDENCE}:
            probability = self.parameter("dropout_probability", "probability", default=1.0)
            if not 0.0 <= probability <= 1.0:
                raise ValueError("dropout probability must be between 0 and 1")
        elif self.fault_type is FaultKind.VALVE_DELAY:
            delay_steps = self.parameter("delay_steps", default=1.0)
            if not delay_steps.is_integer() or not 0.0 <= delay_steps <= 16.0:
                raise ValueError("valve delay_steps must be an integer between 0 and 16")
        elif self.fault_type is FaultKind.COOLING_LOSS:
            loss_fraction = self.parameter("loss_fraction", default=1.0)
            remaining_fraction = self.parameter("remaining_fraction", default=1.0 - loss_fraction)
            if not 0.0 <= loss_fraction <= 1.0:
                raise ValueError("cooling loss_fraction must be between 0 and 1")
            if not 0.0 <= remaining_fraction <= 1.0:
                raise ValueError("cooling remaining_fraction must be between 0 and 1")
        return self

    def parameter(self, *names: str, default: float) -> float:
        for name in names:
            if name in self.parameters:
                return self.parameters[name]
        return default

    def is_active(self, step: int) -> bool:
        if not isinstance(step, int) or isinstance(step, bool):
            return False
        return self.start_step <= step < self.start_step + self.duration

    def active_offset(self, step: int) -> int:
        """Return the one-based number of active steps at ``step``."""

        return max(0, step - self.start_step + 1)

    def _probability_is_active(self, step: int) -> bool:
        probability = self.parameter("dropout_probability", "probability", default=1.0)
        if probability >= 1.0:
            return True
        if probability <= 0.0:
            return False
        digest = hashlib.sha256(f"{self.fault_id}:{step}".encode()).digest()
        sample = int.from_bytes(digest[:8], "big") / float(2**64 - 1)
        return sample < probability

    def is_evidence_missing(self, step: int) -> bool:
        return (
            self.fault_type is FaultKind.MISSING_EVIDENCE
            and self.is_active(step)
            and self._probability_is_active(step)
        )

    def reset_runtime(self) -> None:
        """Clear state used by the valve-delay fault between simulations."""

        self._action_history.clear()

    def modify_action(
        self,
        step_index: int,
        action: ManipulatedVariables | dict[str, Any],
    ) -> ManipulatedVariables:
        """Apply an active actuator fault to one bounded control action."""

        parsed = (
            action
            if isinstance(action, ManipulatedVariables)
            else ManipulatedVariables.model_validate(action)
        )
        step = step_index + 1

        if self.fault_type is FaultKind.VALVE_DELAY:
            self._action_history.append(parsed.model_copy(deep=True))
            if not self.is_active(step):
                return parsed
            delay_steps = int(self.parameter("delay_steps", default=1.0))
            if delay_steps == 0 or len(self._action_history) <= delay_steps:
                return parsed
            delayed = self._action_history[-delay_steps - 1]
            return parsed.model_copy(update={"valve_opening": delayed.valve_opening})

        if self.fault_type is FaultKind.COOLING_LOSS and self.is_active(step):
            if "remaining_fraction" in self.parameters:
                remaining_fraction = self.parameter("remaining_fraction", default=1.0)
            else:
                remaining_fraction = 1.0 - self.parameter("loss_fraction", default=1.0)
            return parsed.model_copy(
                update={"coolant_flow": parsed.coolant_flow * remaining_fraction}
            )

        return parsed

    def _measurement_name(self) -> str:
        name = self.target_asset.strip().lower().replace("-", "_")
        for suffix in ("_sensor", "_probe", "_transmitter"):
            if name.endswith(suffix):
                name = name[: -len(suffix)]
                break
        if name.startswith("sensor_"):
            name = name.removeprefix("sensor_")
        return {"temp": "temperature", "conc": "concentration"}.get(name, name)

    def _with_fault_metadata(self, observation: ProcessObservation) -> ProcessObservation:
        metadata = dict(observation.metadata)
        entries = metadata.get("faults", [])
        entries = list(entries) if isinstance(entries, list) else []
        entries.append(
            {
                "fault_id": self.fault_id,
                "fault_type": self.fault_type.value,
                "target_asset": self.target_asset,
                "step": observation.step,
            }
        )
        metadata["faults"] = entries

        provenance_metadata = dict(observation.provenance.metadata)
        fault_ids = provenance_metadata.get("fault_ids", [])
        fault_ids = list(fault_ids) if isinstance(fault_ids, list) else []
        if self.fault_id not in fault_ids:
            fault_ids.append(self.fault_id)
        provenance_metadata["fault_ids"] = fault_ids
        provenance = observation.provenance.model_copy(
            update={"metadata": provenance_metadata}
        )
        return observation.model_copy(
            update={"metadata": metadata, "provenance": provenance}
        )

    def modify_observation(self, observation: ProcessObservation) -> ProcessObservation:
        """Apply active sensor/evidence faults while retaining true process state."""

        if not self.is_active(observation.step):
            return observation

        modified = observation
        if self.fault_type is FaultKind.SENSOR_DRIFT:
            sensor = self._measurement_name()
            measurements = dict(modified.measurements)
            if sensor in measurements:
                rate = self.parameter("drift_per_step", "rate", "magnitude", default=0.0)
                max_offset = self.parameter("max_offset", default=100.0)
                offset = max(
                    -max_offset,
                    min(max_offset, rate * self.active_offset(observation.step)),
                )
                measurements[sensor] += offset
                reliability = dict(modified.sensor_reliability)
                reliability[sensor] = min(reliability.get(sensor, 1.0), 0.8)
                modified = modified.model_copy(
                    update={
                        "measurements": measurements,
                        "sensor_reliability": reliability,
                    }
                )
        elif (
            self.fault_type is FaultKind.SENSOR_DROPOUT
            and self._probability_is_active(observation.step)
        ):
            sensor = self._measurement_name()
            measurements = dict(modified.measurements)
            measurements.pop(sensor, None)
            reliability = dict(modified.sensor_reliability)
            reliability[sensor] = 0.0
            alarms = list(modified.alarms)
            if "sensor_dropout" not in alarms:
                alarms.append("sensor_dropout")
            modified = modified.model_copy(
                update={
                    "measurements": measurements,
                    "sensor_reliability": reliability,
                    "alarms": alarms,
                }
            )
        elif self.fault_type is FaultKind.MISSING_EVIDENCE:
            if not self.is_evidence_missing(observation.step):
                return observation
            metadata = dict(modified.metadata)
            metadata["evidence_missing"] = True
            modified = modified.model_copy(update={"metadata": metadata})

        return self._with_fault_metadata(modified)


__all__ = ["FaultKind", "FaultSpec", "FaultType"]
