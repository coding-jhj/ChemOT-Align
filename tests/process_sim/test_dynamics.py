from __future__ import annotations

from pathlib import Path

import pytest

from chemot_align.process_sim.config import CSTRConfig
from chemot_align.process_sim.dynamics import calculate_derivatives
from chemot_align.process_sim.simulator import ProcessSimulator, SimulationInputError
from chemot_align.process_sim.state import ManipulatedVariables

CONFIG_PATH = Path("configs/process/cstr_baseline.yaml")


def test_derivatives_are_finite() -> None:
    config = CSTRConfig.from_yaml(CONFIG_PATH)
    simulator = ProcessSimulator(config)
    state = simulator.reset(seed=7)
    action = ManipulatedVariables(
        feed_flow=1.0,
        coolant_flow=0.5,
        valve_opening=1.0,
        pump_on=True,
    )

    derivatives = calculate_derivatives(state, action, config)

    assert derivatives.is_finite()
    assert derivatives.reaction_rate >= 0.0


def test_more_coolant_lowers_the_temperature_trend() -> None:
    config = CSTRConfig.from_yaml(CONFIG_PATH)
    without_coolant = ProcessSimulator(config)
    with_coolant = ProcessSimulator(config)
    without_coolant.reset(seed=42)
    with_coolant.reset(seed=42)

    low_cooling = without_coolant.step(
        ManipulatedVariables(feed_flow=1.0, coolant_flow=0.0, valve_opening=1.0, pump_on=True)
    )
    high_cooling = with_coolant.step(
        ManipulatedVariables(feed_flow=1.0, coolant_flow=1.5, valve_opening=1.0, pump_on=True)
    )

    assert high_cooling.state.temperature < low_cooling.state.temperature


def test_invalid_control_is_rejected_without_clamping() -> None:
    config = CSTRConfig.from_yaml(CONFIG_PATH)
    simulator = ProcessSimulator(config)
    simulator.reset(seed=1)

    with pytest.raises(SimulationInputError, match="feed_flow"):
        simulator.step(
            {"feed_flow": 99.0, "coolant_flow": 0.5, "valve_opening": 1.0, "pump_on": True}
        )


def test_pump_off_changes_flow_and_preserves_provenance() -> None:
    config = CSTRConfig.from_yaml(CONFIG_PATH)
    simulator = ProcessSimulator(config)
    simulator.reset(seed=17)

    observation = simulator.step(
        ManipulatedVariables(feed_flow=1.0, coolant_flow=0.5, valve_opening=1.0, pump_on=False)
    )

    assert observation.state.flow == 0.0
    assert observation.provenance.status.value == "synthetic"
    assert observation.provenance.seed == 17
