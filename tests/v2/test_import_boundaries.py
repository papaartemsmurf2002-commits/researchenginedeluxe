from __future__ import annotations

import ast
import importlib
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
V2_ROOT = ROOT / "src" / "tradingbotsuite" / "v2"

FORBIDDEN_IMPORTS = {
    "tradingbotsuite.adapters.execution",
    "tradingbotsuite.runtime",
    "tradingbotsuite.live",
    "tradingbotsuite.live_smoke",
    "tradingbotsuite.promotion",
    "tradingbot.live",
    "tradingbot.data.hyperliquid",
}

REQUIRED_MARKERS = (
    "V2-AUDIT-ID:",
    "V2-CONTRACTS:",
    "V2-BOUNDARY:",
    "V2-OWNER:",
)


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
    return imports


def test_v2_modules_do_not_import_live_order_or_runtime_paths() -> None:
    offenders: list[str] = []
    for path in sorted(V2_ROOT.rglob("*.py")):
        for module in _imports(path):
            for forbidden in FORBIDDEN_IMPORTS:
                if module == forbidden or module.startswith(f"{forbidden}."):
                    offenders.append(f"{path.relative_to(ROOT)} imports {module}")

    assert offenders == []


def test_importing_v2_root_does_not_load_forbidden_modules() -> None:
    before = set(sys.modules)
    importlib.import_module("tradingbotsuite.v2")
    loaded = set(sys.modules) - before
    forbidden_loaded = sorted(
        module
        for module in loaded
        for forbidden in FORBIDDEN_IMPORTS
        if module == forbidden or module.startswith(f"{forbidden}.")
    )
    assert forbidden_loaded == []


def test_new_v2_modules_have_audit_markers() -> None:
    missing: list[str] = []
    for path in sorted(V2_ROOT.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        missing_markers = [marker for marker in REQUIRED_MARKERS if marker not in text]
        if missing_markers:
            missing.append(
                f"{path.relative_to(ROOT)} missing {', '.join(missing_markers)}"
            )

    assert missing == []
