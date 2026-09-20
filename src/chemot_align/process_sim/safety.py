from __future__ import annotations

import math

from .config import CSTRConfig
from .state import ProcessObservation, SafetyViolation, ViolationDirection


class SafetyChecker:
    """Emit explicit violations for configured bounds; never mutates observations."""

    def __init__(self, config: CSTRConfig):
        self.config = config

    def check(self, observation: ProcessObservation) -> list[SafetyViolation]:
        state = observation.state
        bounds = self.config.bounds
        limits = {
            "temperature": (state.temperature, bounds.temperature_min, bounds.temperature_max),
            "pressure": (state.pressure, bounds.pressure_min, bounds.pressure_max),
            "flow": (state.flow, bounds.flow_min, bounds.flow_max),
            "concentration": (
                state.concentration,
                bounds.concentration_min,
                bounds.concentration_max,
            ),
            "level": (state.level, bounds.level_min, bounds.level_max),
        }
        violations: list[SafetyViolation] = []
        for variable, (value, lower, upper) in limits.items():
            if not math.isfinite(value):
                violations.append(
                    SafetyViolation(
                        code=f"{variable}_non_finite",
                        variable=variable,
                        value=value,
                        limit=None,
                        direction=ViolationDirection.NON_FINITE,
                        message=f"{variable} is non-finite",
                    )
                )
            elif value < lower:
                violations.append(
                    SafetyViolation(
                        code=f"{variable}_low",
                        variable=variable,
                        value=value,
                        limit=lower,
                        direction=ViolationDirection.LOW,
                        message=f"{variable} is below the configured lower bound",
                    )
                )
            elif value > upper:
                violations.append(
                    SafetyViolation(
                        code=f"{variable}_high",
                        variable=variable,
                        value=value,
                        limit=upper,
                        direction=ViolationDirection.HIGH,
                        message=f"{variable} is above the configured upper bound",
                    )
                )
        return violations
