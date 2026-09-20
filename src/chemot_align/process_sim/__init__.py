"""Deterministic, bounded chemical-process simulation primitives."""

from .config import CSTRConfig, ProcessConfig, SafetyBounds
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
