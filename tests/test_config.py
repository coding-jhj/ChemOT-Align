from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from chemot_align.config import ProjectConfig, healthcheck


def write_config(tmp_path: Path, *, tool_mode: str = "read_only", data_root: str = "data") -> Path:
    data_path = tmp_path / data_root
    if data_root != "missing-data":
        data_path.mkdir(parents=True, exist_ok=True)

    path = tmp_path / "project.yaml"
    path.write_text(
        "project_name: ChemOT-Align\n"
        f"tool_mode: {tool_mode}\n"
        f"data_root: {data_root}\n",
        encoding="utf-8",
    )
    return path


def test_project_config_accepts_read_only_tools(tmp_path: Path) -> None:
    path = write_config(tmp_path)

    config = ProjectConfig.from_yaml(path)

    assert config.project_name == "ChemOT-Align"
    assert config.tool_mode == "read_only"
    assert config.data_root == tmp_path / "data"


def test_project_config_rejects_write_tools(tmp_path: Path) -> None:
    path = write_config(tmp_path, tool_mode="write")

    with pytest.raises(ValueError, match="read_only"):
        ProjectConfig.from_yaml(path)


def test_project_config_rejects_missing_data_root(tmp_path: Path) -> None:
    path = write_config(tmp_path, data_root="missing-data")

    with pytest.raises(ValueError, match="data_root"):
        ProjectConfig.from_yaml(path)


def test_default_project_config_is_read_only() -> None:
    config = ProjectConfig.from_yaml(Path("configs/project.yaml"))

    assert config.project_name == "ChemOT-Align"
    assert config.tool_mode == "read_only"
    config.validate()


def test_healthcheck_reports_structured_states() -> None:
    result = healthcheck(ProjectConfig.from_yaml(Path("configs/project.yaml")))

    assert isinstance(result, dict)
    assert result["project"] == "ChemOT-Align"
    assert result["tool_mode"] == "read_only"
    assert "python" in result
    assert "cuda" in result
    assert "model_probe" in result


def test_spec_hash_manifest_matches_repository_copy() -> None:
    spec_path = Path("docs/superpowers/specs/2026-09-20-chemot-align-design.md")
    sums_path = Path("docs/superpowers/specs/SHA256SUMS")

    expected = None
    for line in sums_path.read_text(encoding="utf-8").splitlines():
        digest, name = line.split(maxsplit=1)
        if name == spec_path.name:
            expected = digest
            break

    assert expected is not None
    actual = hashlib.sha256(spec_path.read_bytes()).hexdigest()
    assert actual == expected


def test_cli_payload_is_json_serializable() -> None:
    config = ProjectConfig.from_yaml(Path("configs/project.yaml"))
    payload = config.model_dump(mode="json")

    assert json.loads(json.dumps(payload))["tool_mode"] == "read_only"
