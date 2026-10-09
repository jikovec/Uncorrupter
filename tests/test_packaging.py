from __future__ import annotations

import tomllib
from pathlib import Path

import file_uncorrupter


ROOT = Path(__file__).resolve().parents[1]


def test_package_and_runtime_share_one_authoritative_version_source():
    configuration = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project = configuration["project"]

    assert project["dynamic"] == ["version"]
    assert "version" not in project
    assert configuration["tool"]["setuptools"]["dynamic"]["version"] == {
        "attr": "file_uncorrupter.__version__"
    }
    assert file_uncorrupter.__version__ == "0.4.0"


def test_development_dependencies_are_declared_separately_from_runtime():
    configuration = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    runtime = configuration["project"]["dependencies"]
    development = configuration["project"]["optional-dependencies"]["dev"]

    assert any(item.startswith("Pillow") for item in runtime)
    assert not any(item.startswith(("pytest", "build")) for item in runtime)
    assert any(item.startswith("pytest") for item in development)
    assert any(item.startswith("build") for item in development)


def test_ci_runs_packaging_capability_and_optional_tool_gates():
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

    assert 'os: [ubuntu-latest, windows-latest]' in workflow
    assert 'python-version: ["3.11", "3.12", "3.13"]' in workflow
    assert "UNCORRUPTER_DISABLE_EXTERNAL_TOOLS" in workflow
    assert "python -m build" in workflow
    assert "tests/test_capabilities.py" in workflow
