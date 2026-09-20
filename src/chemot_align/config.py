from __future__ import annotations

import importlib.metadata
import json
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field

EVIDENCE_STATUSES: tuple[str, ...] = (
    "executed",
    "official_checked",
    "synthetic",
    "inferred",
    "unverified",
    "redacted",
)

_ROOT_FIELDS = {
    "raw_root": "raw",
    "interim_root": "interim",
    "processed_root": "processed",
    "quarantine_root": "quarantine",
    "manifest_root": "manifests",
}


class ProjectConfig(BaseModel):
    """Validated, read-only project configuration."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    project_name: str = "ChemOT-Align"
    schema_version: str = "0.1"
    tool_mode: Literal["read_only"] = "read_only"
    python_version: str = "3.12.3"

    data_root: Path
    raw_root: Path
    interim_root: Path
    processed_root: Path
    quarantine_root: Path
    manifest_root: Path
    model_probe_path: Path

    evidence_statuses: tuple[str, ...] = Field(default=EVIDENCE_STATUSES)

    @classmethod
    def from_yaml(cls, path: Path) -> ProjectConfig:
        """Load and validate a project configuration from YAML."""

        path = Path(path)
        try:
            payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            raise ValueError(f"invalid YAML configuration: {path}") from exc

        if not isinstance(payload, dict):
            raise ValueError(f"configuration must be a YAML mapping: {path}")

        config_dir = path.resolve().parent
        data_root = cls._resolve_path(payload.get("data_root", "data"), config_dir)
        normalized: dict[str, Any] = dict(payload)
        normalized["data_root"] = data_root

        for field_name, directory_name in _ROOT_FIELDS.items():
            value = payload.get(field_name, data_root / directory_name)
            normalized[field_name] = cls._resolve_path(value, config_dir)

        normalized["model_probe_path"] = cls._resolve_path(
            payload.get("model_probe_path", normalized["manifest_root"] / "model_probe.json"),
            config_dir,
        )

        config = cls.model_validate(normalized)
        config.validate()
        return config

    @staticmethod
    def _resolve_path(value: str | Path, base_dir: Path) -> Path:
        resolved = Path(value)
        if not resolved.is_absolute():
            resolved = base_dir / resolved
        return resolved.resolve()

    def validate(self) -> None:
        """Validate semantic project constraints not covered by field types."""

        if not self.project_name.strip():
            raise ValueError("project_name must not be empty")
        if self.tool_mode != "read_only":
            raise ValueError("tool_mode must be read_only")
        if not self.data_root.exists() or not self.data_root.is_dir():
            raise ValueError(f"data_root does not exist or is not a directory: {self.data_root}")
        if tuple(self.evidence_statuses) != EVIDENCE_STATUSES:
            raise ValueError(
                "evidence_statuses must contain exactly: " + ", ".join(EVIDENCE_STATUSES)
            )

    def as_json(self) -> str:
        """Return a stable JSON representation for CLI and manifests."""

        return json.dumps(
            self.model_dump(mode="json"), ensure_ascii=False, indent=2, sort_keys=True
        )


def _package_status(distribution: str) -> str:
    try:
        return f"installed:{importlib.metadata.version(distribution)}"
    except importlib.metadata.PackageNotFoundError:
        return "unavailable"


def _directory_status(path: Path) -> str:
    return "available" if path.exists() and path.is_dir() else "missing"


def _cuda_status() -> str:
    """Probe CUDA in a child process so an optional runtime cannot crash the CLI."""

    probe = (
        "import torch; "
        "print('available' if torch.cuda.is_available() else 'unavailable')"
    )
    try:
        result = subprocess.run(
            [sys.executable, "-c", probe],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return "probe_failed"

    if result.returncode != 0:
        return "probe_failed"
    value = result.stdout.strip().splitlines()[-1] if result.stdout.strip() else ""
    return value if value in {"available", "unavailable"} else "probe_failed"


def healthcheck(config: ProjectConfig | None = None) -> dict[str, str]:
    """Report observed environment and project states without claiming availability."""

    if config is None:
        config = ProjectConfig.from_yaml(Path("configs/project.yaml"))

    observed_python = platform.python_version()
    target_python = config.python_version
    observed_major_minor = ".".join(observed_python.split(".")[:2])
    target_major_minor = ".".join(target_python.split(".")[:2])

    result = {
        "project": config.project_name,
        "schema_version": config.schema_version,
        "tool_mode": config.tool_mode,
        "python": observed_python,
        "python_target": target_python,
        "python_status": (
            "compatible" if observed_major_minor == target_major_minor else "version_mismatch"
        ),
        "pydantic": _package_status("pydantic"),
        "pyyaml": _package_status("PyYAML"),
        "data_root": _directory_status(config.data_root),
        "raw_root": _directory_status(config.raw_root),
        "interim_root": _directory_status(config.interim_root),
        "processed_root": _directory_status(config.processed_root),
        "quarantine_root": _directory_status(config.quarantine_root),
        "manifest_root": _directory_status(config.manifest_root),
        "cuda": _cuda_status(),
        "model_probe": "available" if config.model_probe_path.is_file() else "unavailable",
    }
    return result
