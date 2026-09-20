from __future__ import annotations

import math
import random
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from ..provenance.records import EvidenceStatus, ProvenanceRecord
from .config import CSTRConfig
from .dynamics import calculate_derivatives, integrate_state
from .safety import SafetyChecker
from .state import (
    ManipulatedVariables,
    ProcessObservation,
    ProcessState,
    SimulationInputError,
)


class ProcessSimulator:
    """Seed-reproducible, offline CSTR simulator with bounded controls."""

    def __init__(self, config: CSTRConfig | Path):
        self.config = CSTRConfig.from_yaml(config) if isinstance(config, Path) else config
        self.safety_checker = SafetyChecker(self.config)
        self._rng = random.Random()
        self._state: ProcessState | None = None
        self._seed: int | None = None

    @property
    def state(self) -> ProcessState | None:
        return self._state.model_copy(deep=True) if self._state is not None else None

    def reset(self, seed: int) -> ProcessState:
        if not isinstance(seed, int) or isinstance(seed, bool):
            raise SimulationInputError("seed must be an integer")
        self._seed = seed
        self._rng = random.Random(seed)
        self._state = self.config.initial_state()
        return self._state.model_copy(deep=True)

    def _coerce_action(self, action: ManipulatedVariables | dict[str, Any]) -> ManipulatedVariables:
        try:
            parsed = (
                action
                if isinstance(action, ManipulatedVariables)
                else ManipulatedVariables.model_validate(action)
            )
        except (ValidationError, TypeError, ValueError) as exc:
            raise SimulationInputError(f"invalid manipulated variables: {exc}") from exc

        if parsed.feed_flow > self.config.max_feed_flow:
            raise SimulationInputError("feed_flow exceeds configured maximum")
        if parsed.coolant_flow > self.config.max_coolant_flow:
            raise SimulationInputError("coolant_flow exceeds configured maximum")
        return parsed

    def step(self, action: ManipulatedVariables | dict[str, Any]) -> ProcessObservation:
        if self._state is None or self._seed is None:
            raise SimulationInputError("reset(seed) must be called before step")

        parsed_action = self._coerce_action(action)
        derivatives = calculate_derivatives(self._state, parsed_action, self.config)
        next_state = integrate_state(self._state, parsed_action, derivatives, self.config)
        self._state = next_state

        measurements = {
            "temperature": self._measure(next_state.temperature),
            "pressure": self._measure(next_state.pressure),
            "flow": self._measure(next_state.flow),
            "concentration": self._measure(next_state.concentration),
            "level": self._measure(next_state.level),
        }
        observation = ProcessObservation(
            step=next_state.step,
            state=next_state,
            measurements=measurements,
            sensor_reliability={name: 1.0 for name in measurements},
            diagnostics=derivatives.model_dump(mode="python"),
            provenance=ProvenanceRecord(
                source_reference=(
                    f"synthetic://process/{self.config.name}/seed/{self._seed}/step/{next_state.step}"
                ),
                status=EvidenceStatus.SYNTHETIC,
                seed=self._seed,
                environment={"producer": "ProcessSimulator", "config": self.config.name},
            ),
        )
        violations = self.safety_checker.check(observation)
        return observation.model_copy(
            update={
                "alarms": [violation.code for violation in violations],
                "safety_violations": violations,
            }
        )

    def simulate(
        self,
        steps: int,
        seed: int,
        faults: tuple[Any, ...] = (),
    ) -> list[ProcessObservation]:
        if not isinstance(steps, int) or isinstance(steps, bool) or steps < 0:
            raise SimulationInputError("steps must be a non-negative integer")

        self.reset(seed)
        for fault in faults:
            reset_runtime = getattr(fault, "reset_runtime", None)
            if reset_runtime is not None:
                reset_runtime()
        observations: list[ProcessObservation] = []
        for step_index in range(steps):
            action: ManipulatedVariables | dict[str, Any] = self.config.default_action
            for fault in faults:
                modifier = getattr(fault, "modify_action", None)
                if modifier is not None:
                    action = modifier(step_index, action)
            observation = self.step(action)
            for fault in faults:
                modifier = getattr(fault, "modify_observation", None)
                if modifier is not None:
                    observation = modifier(observation)
            observations.append(observation)
        return observations

    def _measure(self, value: float) -> float:
        if self.config.measurement_noise_std == 0.0:
            return value
        measured = value + self._rng.gauss(0.0, self.config.measurement_noise_std)
        if not math.isfinite(measured):
            raise SimulationInputError("non-finite sensor measurement")
        return measured
