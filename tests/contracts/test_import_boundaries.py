from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RESEARCH_ROOT = ROOT / "src" / "tradingbotsuite" / "research"
DATA_ROOT = ROOT / "src" / "tradingbotsuite" / "data"
FEATURES_ROOT = ROOT / "src" / "tradingbotsuite" / "features"
BACKTESTING_ROOT = ROOT / "src" / "tradingbotsuite" / "backtesting"
STRATEGIES_ROOT = ROOT / "src" / "tradingbotsuite" / "strategies"
CONTRACT_ROOT = ROOT / "docs" / "contracts"

FORBIDDEN_RESEARCH_IMPORTS = {
    "tradingbotsuite.adapters.execution",
    "tradingbotsuite.runtime",
    "tradingbotsuite.live_smoke",
    "tradingbot.live",
    "tradingbot.data.hyperliquid",
}

REQUIRED_CONTRACTS = {
    "README.md",
    "data_contract.md",
    "feature_contract.md",
    "strategy_contract.md",
    "backtest_contract.md",
    "artifact_contract.md",
    "promotion_contract.md",
    "boundary_contract.md",
}


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
    return imports


def test_research_modules_do_not_import_order_placement_paths() -> None:
    offenders: list[str] = []
    for path in sorted(RESEARCH_ROOT.rglob("*.py")):
        for module in _imports(path):
            for forbidden in FORBIDDEN_RESEARCH_IMPORTS:
                if module == forbidden or module.startswith(f"{forbidden}."):
                    offenders.append(f"{path.relative_to(ROOT)} imports {module}")

    assert offenders == []


def test_data_modules_do_not_import_order_placement_paths() -> None:
    offenders: list[str] = []
    for path in sorted(DATA_ROOT.rglob("*.py")):
        for module in _imports(path):
            for forbidden in FORBIDDEN_RESEARCH_IMPORTS:
                if module == forbidden or module.startswith(f"{forbidden}."):
                    offenders.append(f"{path.relative_to(ROOT)} imports {module}")

    assert offenders == []


def test_feature_modules_do_not_import_order_placement_paths() -> None:
    offenders: list[str] = []
    for path in sorted(FEATURES_ROOT.rglob("*.py")):
        for module in _imports(path):
            for forbidden in FORBIDDEN_RESEARCH_IMPORTS:
                if module == forbidden or module.startswith(f"{forbidden}."):
                    offenders.append(f"{path.relative_to(ROOT)} imports {module}")

    assert offenders == []


def test_backtesting_modules_do_not_import_order_placement_paths() -> None:
    offenders: list[str] = []
    for path in sorted(BACKTESTING_ROOT.rglob("*.py")):
        for module in _imports(path):
            for forbidden in FORBIDDEN_RESEARCH_IMPORTS:
                if module == forbidden or module.startswith(f"{forbidden}."):
                    offenders.append(f"{path.relative_to(ROOT)} imports {module}")

    assert offenders == []


def test_strategy_modules_do_not_import_order_placement_paths() -> None:
    offenders: list[str] = []
    for path in sorted(STRATEGIES_ROOT.rglob("*.py")):
        for module in _imports(path):
            for forbidden in FORBIDDEN_RESEARCH_IMPORTS:
                if module == forbidden or module.startswith(f"{forbidden}."):
                    offenders.append(f"{path.relative_to(ROOT)} imports {module}")

    assert offenders == []


def test_stage_two_contract_docs_exist() -> None:
    existing = {path.name for path in CONTRACT_ROOT.glob("*.md")}
    assert REQUIRED_CONTRACTS <= existing
