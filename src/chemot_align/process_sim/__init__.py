"""Deterministic, bounded chemical-process simulation primitives."""

from .config import CSTRConfig, ProcessConfig, SafetyBounds
from .faults import FaultKind, FaultSpec, FaultType
from .safety import SafetyChecker
from .simulator import ProcessSimulator, SimulationInputError
from .state import (
    ManipulatedVariables,
    ProcessObservation,
    ProcessState,
    SafetyViolation,
)

__all__ = [
    "CSTRConfig",
    "FaultKind",
    "FaultSpec",
    "FaultType",
    "ManipulatedVariables",
    "ProcessConfig",
    "ProcessObservation",
    "ProcessSimulator",
    "ProcessState",
    "SafetyBounds",
    "SafetyChecker",
    "SafetyViolation",
    "SimulationInputError",
]
