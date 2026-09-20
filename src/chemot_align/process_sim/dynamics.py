from __future__ import annotations

import math

from pydantic import BaseModel, ConfigDict, Field

from .config import CSTRConfig
from .state import ManipulatedVariables, ProcessState, SimulationInputError


class DynamicsResult(BaseModel):
    """Intermediate values exposed for deterministic simulator tests."""

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    d_concentration_dt: float
    d_temperature_dt: float
    d_pressure_dt: float
    d_level_dt: float
    reaction_rate: float = Field(ge=0.0)
    effective_flow: float = Field(ge=0.0)
    heat_transfer: float

    def is_finite(self) -> bool:
        return all(math.isfinite(value) for value in self.model_dump().values())


def rate_constant(temperature: float, config: CSTRConfig) -> float:
    if not math.isfinite(temperature) or temperature <= 0.0:
        raise SimulationInputError("temperature must be finite and greater than zero")

    exponent = config.activation_energy / config.gas_constant * (
        1.0 / config.reference_temperature - 1.0 / temperature
    )
    value = config.rate_constant_reference * math.exp(exponent)
    return min(value, config.max_rate_constant)


def calculate_derivatives(
    state: ProcessState,
    action: ManipulatedVariables,
    config: CSTRConfig,
) -> DynamicsResult:
    """Calculate a bounded Euler step for the documented constant-volume model."""

    effective_flow = action.feed_flow * action.valve_opening if action.pump_on else 0.0
    reaction_rate = rate_constant(state.temperature, config) * state.concentration
    heat_transfer = -config.coolant_heat_transfer * action.coolant_flow

    d_concentration_dt = (
        effective_flow / config.volume * (config.feed_concentration - state.concentration)
        - reaction_rate
    )
    d_temperature_dt = (
        effective_flow / config.volume * (config.feed_temperature - state.temperature)
        + config.reaction_heat / (config.density * config.heat_capacity)
        + heat_transfer / (config.density * config.heat_capacity * config.volume)
    )
    d_pressure_dt = config.pressure_relaxation * (
        state.concentration - config.feed_concentration
    ) + config.pressure_flow_gain * (effective_flow - config.nominal_outflow)
    d_level_dt = (effective_flow - config.nominal_outflow) / config.volume

    result = DynamicsResult(
        d_concentration_dt=d_concentration_dt,
        d_temperature_dt=d_temperature_dt,
        d_pressure_dt=d_pressure_dt,
        d_level_dt=d_level_dt,
        reaction_rate=max(0.0, reaction_rate),
        effective_flow=effective_flow,
        heat_transfer=heat_transfer,
    )
    if not result.is_finite():
        raise SimulationInputError("non-finite process derivative")
    return result


def integrate_state(
    state: ProcessState,
    action: ManipulatedVariables,
    derivatives: DynamicsResult,
    config: CSTRConfig,
) -> ProcessState:
    """Integrate one step without clamping out-of-bound values."""

    return ProcessState(
        step=state.step + 1,
        time=state.time + config.dt,
        temperature=state.temperature + config.dt * derivatives.d_temperature_dt,
        pressure=state.pressure + config.dt * derivatives.d_pressure_dt,
        flow=derivatives.effective_flow,
        concentration=state.concentration + config.dt * derivatives.d_concentration_dt,
        level=state.level + config.dt * derivatives.d_level_dt,
        feed_flow=action.feed_flow,
        coolant_flow=action.coolant_flow,
        valve_opening=action.valve_opening,
        pump_on=action.pump_on,
    )
