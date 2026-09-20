from __future__ import annotations

from pathlib import Path

from chemot_align.process_sim.config import CSTRConfig
from chemot_align.process_sim.safety import SafetyChecker
from chemot_align.process_sim.simulator import ProcessSimulator


def test_safety_checker_emits_temperature_violation_at_configured_bound() -> None:
    base_config = CSTRConfig.from_yaml(Path("configs/process/cstr_baseline.yaml"))
    bounds = base_config.bounds.model_copy(update={"temperature_max": 300.0})
    config = base_config.model_copy(update={"bounds": bounds})
    observation = ProcessSimulator(config).simulate(steps=1, seed=9)[0]

    violations = SafetyChecker(config).check(observation)

    assert any(item.code == "temperature_high" for item in violations)
    assert any(item.variable == "temperature" for item in violations)
