from __future__ import annotations

from pathlib import Path

from chemot_align.process_sim.config import CSTRConfig
from chemot_align.process_sim.simulator import ProcessSimulator


def test_same_seed_produces_identical_observations() -> None:
    config = CSTRConfig.from_yaml(Path("configs/process/cstr_baseline.yaml"))

    first = ProcessSimulator(config).simulate(steps=8, seed=123)
    second = ProcessSimulator(config).simulate(steps=8, seed=123)

    assert [item.model_dump(mode="json") for item in first] == [
        item.model_dump(mode="json") for item in second
    ]


def test_zero_steps_returns_no_observations() -> None:
    config = CSTRConfig.from_yaml(Path("configs/process/cstr_baseline.yaml"))

    assert ProcessSimulator(config).simulate(steps=0, seed=123) == []


def test_simulation_observations_have_finite_state_values() -> None:
    config = CSTRConfig.from_yaml(Path("configs/process/cstr_baseline.yaml"))

    observations = ProcessSimulator(config).simulate(steps=4, seed=5)

    assert observations
    for observation in observations:
        assert all(
            value == value and abs(value) != float("inf")
            for value in observation.state.model_dump().values()
            if isinstance(value, float)
        )
