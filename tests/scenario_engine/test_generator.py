from __future__ import annotations

from pathlib import Path

import pytest

from chemot_align.provenance.records import EvidenceStatus
from chemot_align.scenario_engine.generator import ScenarioGenerator
from chemot_align.scenario_engine.specs import ScenarioSpec
from chemot_align.schemas.model_output import IncidentClass

SCENARIO_DIR = Path("scenarios/process")


def test_scenario_spec_records_source_hash() -> None:
    path = SCENARIO_DIR / "normal_cstr.yaml"

    spec = ScenarioSpec.from_yaml(path)

    assert spec.source_hash
    assert spec.source_path == str(path.resolve())
    assert spec.faults == ()


@pytest.mark.parametrize(
    "scenario_name, expected_class",
    [
        ("normal_cstr.yaml", IncidentClass.NORMAL),
        ("sensor_drift.yaml", IncidentClass.SENSOR_FAULT),
        ("valve_delay.yaml", IncidentClass.PROCESS_FAULT),
        ("cooling_loss.yaml", IncidentClass.PROCESS_FAULT),
    ],
)
def test_scenario_generator_builds_valid_incident_cases(
    scenario_name: str, expected_class: IncidentClass
) -> None:
    spec = ScenarioSpec.from_yaml(SCENARIO_DIR / scenario_name)
    case = ScenarioGenerator().generate(spec, seed=21)

    assert case.ground_truth.incident_class == expected_class
    assert case.provenance.status == EvidenceStatus.SYNTHETIC
    assert case.provenance.source_hash == spec.source_hash
    assert case.provenance.seed == 21
    assert case.evidence
    assert all(item.trust_level.value == "synthetic" for item in case.evidence)
    assert all(
        item.provenance is not None
        and item.provenance.status == EvidenceStatus.SYNTHETIC
        for item in case.evidence
    )


def test_scenario_generation_is_deterministic_from_family_and_seed() -> None:
    spec = ScenarioSpec.from_yaml(SCENARIO_DIR / "sensor_drift.yaml")
    generator = ScenarioGenerator()

    first = generator.generate(spec, seed=99)
    second = generator.generate(spec, seed=99)

    assert first.case_id == second.case_id
    assert first.model_dump(mode="json") == second.model_dump(mode="json")
