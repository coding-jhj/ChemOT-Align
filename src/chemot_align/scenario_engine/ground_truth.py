from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any

from ..process_sim.faults import FaultKind, FaultSpec
from ..process_sim.state import ProcessObservation
from ..schemas.incident import GroundTruth
from ..schemas.model_output import IncidentClass, Severity


def _unique(values: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value and value.strip()))


class GroundTruthBuilder:
    """Derive conservative incident labels from synthetic observations and faults."""

    @classmethod
    def from_observations(
        cls,
        observations: Sequence[ProcessObservation],
        faults: Sequence[FaultSpec] = (),
        scenario: Any | None = None,
        evidence_ids: Sequence[str] = (),
        required_evidence: Sequence[str] = (),
        missing_evidence: Sequence[str] = (),
    ) -> GroundTruth:
        if not isinstance(faults, (list, tuple)) and hasattr(faults, "faults"):
            scenario = faults
            faults = tuple(getattr(scenario, "faults", ()))

        faults = tuple(faults)
        fault_kinds = {fault.fault_type for fault in faults}
        sensor_fault = bool(fault_kinds & {FaultKind.SENSOR_DRIFT, FaultKind.SENSOR_DROPOUT})
        process_fault = bool(fault_kinds & {FaultKind.VALVE_DELAY, FaultKind.COOLING_LOSS})
        missing_fault = FaultKind.MISSING_EVIDENCE in fault_kinds
        violations = [violation for item in observations for violation in item.safety_violations]

        if sensor_fault and process_fault:
            derived_class = IncidentClass.COMBINED
        elif sensor_fault:
            derived_class = IncidentClass.SENSOR_FAULT
        elif process_fault or violations or missing_fault:
            derived_class = IncidentClass.PROCESS_FAULT
        else:
            derived_class = IncidentClass.NORMAL

        if derived_class is IncidentClass.NORMAL:
            derived_severity = Severity.INFORMATIONAL
        elif derived_class is IncidentClass.SENSOR_FAULT:
            derived_severity = Severity.LOW
        elif derived_class is IncidentClass.COMBINED:
            derived_severity = Severity.HIGH
        else:
            derived_severity = Severity.MEDIUM
        if any(item.direction.value == "non_finite" for item in violations):
            derived_severity = Severity.CRITICAL
        elif any(item.direction.value == "high" for item in violations):
            derived_severity = Severity.HIGH

        hints = getattr(scenario, "ground_truth", None)
        incident_class = getattr(hints, "incident_class", None) or derived_class
        severity = getattr(hints, "severity", None) or derived_severity

        fault_labels = [fault.label for fault in faults]
        root_cause = _unique(getattr(hints, "root_cause_class", []) or fault_labels)
        if not root_cause:
            root_cause = _unique(fault.fault_type.value for fault in faults)
        affected_assets = _unique(
            getattr(hints, "affected_assets", [])
            or [fault.target_asset for fault in faults]
        )

        expected_evidence = _unique(required_evidence or evidence_ids)
        missing_ids = _unique(missing_evidence)
        if missing_fault and not missing_ids:
            missing_ids = _unique(
                f"fault:{fault.fault_id}"
                for fault in faults
                if fault.fault_type is FaultKind.MISSING_EVIDENCE
            )

        process_impact = list(getattr(hints, "process_impact", []) or [])
        if not process_impact:
            impact_by_kind = {
                FaultKind.SENSOR_DRIFT: "A sensor reading can diverge from the true process state.",
                FaultKind.SENSOR_DROPOUT: "A process sensor can become unavailable.",
                FaultKind.VALVE_DELAY: "The manipulated valve response is delayed.",
                FaultKind.COOLING_LOSS: "Available cooling capacity is reduced.",
                FaultKind.MISSING_EVIDENCE: (
                    "Required process evidence is unavailable for part of the window."
                ),
            }
            process_impact = _unique(impact_by_kind[fault.fault_type] for fault in faults)
            if violations:
                process_impact.append("One or more configured safety bounds were crossed.")
            if not process_impact and observations:
                process_impact = ["No configured process fault was injected."]

        security_impact = list(getattr(hints, "security_impact", []) or [])
        safe_next_actions = list(getattr(hints, "safe_next_actions", []) or [])
        if not safe_next_actions:
            safe_next_actions = [
                "inspect_process_state",
                "verify_sensor_health",
                "preserve_provenance_and_observations",
            ]
        verification_steps = list(getattr(hints, "verification_steps", []) or [])
        if not verification_steps:
            verification_steps = [
                "compare measurements with the simulated true state",
                "verify the active fault window and seed",
            ]

        hinted_abstain = getattr(hints, "should_abstain", None)
        should_abstain = bool(missing_ids) or not observations
        if hinted_abstain is not None:
            should_abstain = hinted_abstain
        abstention_reason = getattr(hints, "abstention_reason", None)
        if should_abstain and not abstention_reason:
            abstention_reason = (
                "Required process evidence is missing."
                if missing_ids
                else "No process observations were generated."
            )

        return GroundTruth(
            incident_class=incident_class,
            severity=severity,
            root_cause_class=root_cause,
            affected_assets=affected_assets,
            required_evidence=expected_evidence,
            missing_evidence=missing_ids,
            process_impact=_unique(process_impact),
            security_impact=_unique(security_impact),
            safe_next_actions=_unique(safe_next_actions),
            verification_steps=_unique(verification_steps),
            should_abstain=should_abstain,
            abstention_reason=abstention_reason,
        )


__all__ = ["GroundTruthBuilder"]
