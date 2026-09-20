from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from chemot_align.process_sim.config import CSTRConfig
from chemot_align.process_sim.faults import FaultKind, FaultSpec
from chemot_align.process_sim.simulator import ProcessSimulator
from chemot_align.process_sim.state import ManipulatedVariables

CONFIG_PATH = Path("configs/process/cstr_baseline.yaml")


def make_fault(
    fault_type: FaultKind,
    *,
    start_step: int = 2,
    duration: int = 3,
    target_asset: str = "temperature_sensor",
    parameters: dict[str, float] | None = None,
) -> FaultSpec:
    return FaultSpec(
        fault_id=f"{fault_type.value}-001",
        fault_type=fault_type,
        start_step=start_step,
        duration=duration,
        target_asset=target_asset,
        parameters=parameters or {},
        label=f"{fault_type.value} test fault",
    )


def test_sensor_drift_changes_measurement_but_not_true_state() -> None:
    config = CSTRConfig.from_yaml(CONFIG_PATH)
    clean = ProcessSimulator(config).simulate(steps=4, seed=4)
    faulty = ProcessSimulator(config).simulate(
        steps=4,
        seed=4,
        faults=(
            make_fault(
                FaultKind.SENSOR_DRIFT,
                parameters={"drift_per_step": 1.0},
            ),
        ),
    )

    assert faulty[1].measurements["temperature"] > clean[1].measurements["temperature"]
    assert faulty[1].state.temperature == clean[1].state.temperature
    assert faulty[1].provenance.metadata["fault_ids"] == ["sensor_drift-001"]


def test_sensor_dropout_removes_measurement_and_marks_reliability() -> None:
    config = CSTRConfig.from_yaml(CONFIG_PATH)
    observations = ProcessSimulator(config).simulate(
        steps=3,
        seed=4,
        faults=(
            make_fault(FaultKind.SENSOR_DROPOUT),
        ),
    )

    assert "temperature" not in observations[1].measurements
    assert observations[1].sensor_reliability["temperature"] == 0.0
    assert "sensor_dropout" in observations[1].alarms


def test_cooling_loss_reduces_coolant_action_and_changes_temperature() -> None:
    config = CSTRConfig.from_yaml(CONFIG_PATH)
    clean = ProcessSimulator(config).simulate(steps=3, seed=8)
    faulty = ProcessSimulator(config).simulate(
        steps=3,
        seed=8,
        faults=(
            make_fault(
                FaultKind.COOLING_LOSS,
                target_asset="coolant_pump",
                start_step=1,
                duration=3,
                parameters={"loss_fraction": 0.8},
            ),
        ),
    )

    assert faulty[0].state.coolant_flow < clean[0].state.coolant_flow
    assert faulty[0].state.temperature > clean[0].state.temperature


def test_valve_delay_uses_previous_bounded_command() -> None:
    fault = make_fault(
        FaultKind.VALVE_DELAY,
        start_step=1,
        duration=3,
        target_asset="feed_valve",
        parameters={"delay_steps": 1},
    )
    first = ManipulatedVariables(
        feed_flow=1.0,
        coolant_flow=0.5,
        valve_opening=0.2,
        pump_on=True,
    )
    second = first.model_copy(update={"valve_opening": 0.8})

    assert fault.modify_action(0, first).valve_opening == 0.2
    assert fault.modify_action(1, second).valve_opening == 0.2


def test_missing_evidence_fault_has_a_bounded_active_window() -> None:
    fault = make_fault(
        FaultKind.MISSING_EVIDENCE,
        start_step=2,
        duration=2,
        target_asset="temperature_sensor",
    )

    assert not fault.is_evidence_missing(1)
    assert fault.is_evidence_missing(2)
    assert fault.is_evidence_missing(3)
    assert not fault.is_evidence_missing(4)


def test_fault_spec_rejects_unknown_faults_and_unsafe_text() -> None:
    with pytest.raises(ValidationError):
        FaultSpec(
            fault_id="unsafe-001",
            fault_type="shell_command",
            start_step=1,
            duration=1,
            target_asset="temperature_sensor",
            parameters={},
            label="unsafe",
        )

    with pytest.raises(ValidationError, match="URL or shell"):
        FaultSpec(
            fault_id="unsafe-001",
            fault_type=FaultKind.SENSOR_DRIFT,
            start_step=1,
            duration=1,
            target_asset="https://example.invalid/target",
            parameters={"drift_per_step": 1.0},
            label="unsafe",
        )
