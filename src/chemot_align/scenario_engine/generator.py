from __future__ import annotations

import hashlib
import re
from pathlib import Path

from ..process_sim.config import CSTRConfig
from ..process_sim.simulator import ProcessSimulator
from ..provenance.records import EvidenceStatus, ProvenanceRecord
from ..schemas.evidence import Evidence, IntegrityStatus, SourceLayer, TrustLevel
from ..schemas.incident import IncidentCase
from .ground_truth import GroundTruthBuilder
from .specs import ScenarioSpec


class ScenarioGenerator:
    """Generate schema-valid, seed-reproducible synthetic incident cases."""

    def __init__(self, repo_root: Path | None = None):
        self.repo_root = Path(repo_root).resolve() if repo_root is not None else None

    def generate(self, spec: ScenarioSpec | Path | str, seed: int) -> IncidentCase:
        if isinstance(spec, (str, Path)):
            spec = ScenarioSpec.from_yaml(Path(spec))
        if not isinstance(seed, int) or isinstance(seed, bool):
            raise ValueError("seed must be an integer")

        process_config_path = spec.resolve_process_config(self.repo_root)
        config = CSTRConfig.from_yaml(process_config_path)
        faults = tuple(fault.model_copy(deep=True) for fault in spec.faults)
        observations = ProcessSimulator(config).simulate(
            steps=spec.steps,
            seed=seed,
            faults=faults,
        )

        case_id = self._case_id(spec.scenario_family, seed)
        evidence: list[Evidence] = []
        expected_evidence_ids: list[str] = []
        missing_evidence_ids: list[str] = []
        for observation in observations:
            evidence_id = f"{case_id}:process:{observation.step:05d}"
            expected_evidence_ids.append(evidence_id)
            if any(fault.is_evidence_missing(observation.step) for fault in faults):
                missing_evidence_ids.append(evidence_id)
                continue
            evidence.append(self._to_evidence(evidence_id, config.name, observation))

        ground_truth = GroundTruthBuilder.from_observations(
            observations,
            faults=faults,
            scenario=spec,
            evidence_ids=[item.evidence_id for item in evidence],
            required_evidence=expected_evidence_ids,
            missing_evidence=missing_evidence_ids,
        )
        provenance = ProvenanceRecord(
            source_reference=f"scenario://{spec.scenario_id}",
            status=EvidenceStatus.SYNTHETIC,
            source_hash=spec.source_hash,
            seed=seed,
            environment={
                "producer": "ScenarioGenerator",
                "scenario_id": spec.scenario_id,
                "scenario_family": spec.scenario_family,
                "process_config": spec.process_config,
            },
            metadata={
                "fault_ids": [fault.fault_id for fault in faults],
                "observation_count": len(observations),
                "evidence_count": len(evidence),
            },
        )
        return IncidentCase(
            case_id=case_id,
            scenario_family=spec.scenario_family,
            seed=seed,
            evidence=evidence,
            ground_truth=ground_truth,
            allowed_actions=list(spec.allowed_actions),
            forbidden_actions=list(spec.forbidden_actions),
            provenance=provenance,
        )

    @staticmethod
    def _case_id(scenario_family: str, seed: int) -> str:
        digest = hashlib.sha256(f"{scenario_family}:{seed}".encode()).hexdigest()[:12]
        family = re.sub(r"[^a-z0-9]+", "-", scenario_family.lower()).strip("-") or "scenario"
        return f"case-{family}-{digest}"

    @staticmethod
    def _to_evidence(evidence_id: str, asset_id: str, observation) -> Evidence:
        content = {
            "state": observation.state.model_dump(mode="json"),
            "measurements": observation.measurements,
            "alarms": observation.alarms,
            "safety_violations": [
                violation.model_dump(mode="json")
                for violation in observation.safety_violations
            ],
            "sensor_reliability": observation.sensor_reliability,
            "diagnostics": observation.diagnostics,
            "metadata": observation.metadata,
        }
        return Evidence(
            evidence_id=evidence_id,
            timestamp=f"t+{observation.state.time:.3f}s",
            source_layer=SourceLayer.PROCESS,
            asset_id=asset_id,
            event_type="process_observation",
            content=content,
            trust_level=TrustLevel.SYNTHETIC,
            integrity_status=IntegrityStatus.INTACT,
            source_reference=observation.provenance.source_reference,
            provenance=observation.provenance,
        )


__all__ = ["ScenarioGenerator"]
