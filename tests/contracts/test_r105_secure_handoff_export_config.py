from __future__ import annotations

import fnmatch
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = REPO_ROOT / "configs" / "handoff" / "r105_secure_repo_export.json"


def test_r105_secure_handoff_export_config_is_security_first() -> None:
    payload = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))

    assert payload["config_version"] == "r105-secure-repo-export-v1"
    assert payload["security"]["enableSecurityCheck"] is True
    assert payload["security"]["blockOnPotentialSecret"] is True
    assert payload["research_boundary"]["research_only"] is True
    assert payload["research_boundary"]["observe_only"] is True
    assert payload["research_boundary"]["promotion_ready"] is False
    assert payload["research_boundary"]["live_execution_input"] is False
    assert payload["research_boundary"]["runtime_control_input"] is False


def test_r105_secure_handoff_export_config_excludes_risky_artifacts() -> None:
    payload = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    include = set(payload["include"])
    ignore = payload["ignore"]
    custom_patterns = set(ignore["customPatterns"])

    assert {"src/**/*.py", "configs/**/*.json", "docs/**/*.md", "tests/**/*.py"} <= include
    assert ignore["useGitignore"] is True
    assert ignore["useDotIgnore"] is True
    assert ignore["useDefaultPatterns"] is True
    assert {
        "data/**",
        "**/.env*",
        "**/*secret*",
        "**/*api_key*",
        "**/*private_key*",
        "**/*secret_key*",
        "**/*credential*",
        "**/operator_runs/**",
        "**/cache/**",
        "**/*.parquet",
        "**/*.db",
        "**/*.sqlite",
        "**/*.log",
    } <= custom_patterns
    assert "**/*key*" not in custom_patterns
    assert not any(
        fnmatch.fnmatch(path, pattern)
        for path in (
            "src/tradingbotsuite/research_discovery/artifact_keys.py",
            "tests/research_discovery/test_artifact_keys.py",
        )
        for pattern in custom_patterns
    )
