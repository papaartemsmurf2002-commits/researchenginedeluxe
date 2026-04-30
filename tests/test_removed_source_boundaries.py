from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ACTIVE_ROOTS = [
    ROOT / "README.md",
    ROOT / "pyproject.toml",
    ROOT / "configs",
    ROOT / "examples",
    ROOT / "src",
    ROOT / "tests",
]
SKIP_DIRS = {".git", ".hypothesis", ".pytest_cache", ".venv", "__pycache__"}
SKIP_FILES = {
    Path(__file__).resolve(),
}
TEXT_SUFFIXES = {".html", ".json", ".md", ".py", ".toml", ".txt", ".yaml", ".yml"}


def _iter_text_files() -> list[Path]:
    files: list[Path] = []
    for root in ACTIVE_ROOTS:
        if root.is_file():
            files.append(root)
            continue
        for path in root.rglob("*"):
            if not path.is_file() or path.resolve() in SKIP_FILES:
                continue
            if any(part in SKIP_DIRS for part in path.parts):
                continue
            if path.suffix.lower() in TEXT_SUFFIXES:
                files.append(path)
    return files


def test_removed_vendor_source_surfaces_stay_out_of_active_tree() -> None:
    disallowed = [
        "Trading" + "View",
        "trading" + "view",
        "chart" + "_export",
        "chart" + "-export",
        "tv" + "_bar_time_ms",
        "entry" + "_gate",
        "entry" + "-gate",
        "parity" + "-check",
        "entry" + "-parity",
        "merge" + "-tv",
        "marker" + "-research",
        "serve" + "-ui",
        "features" + "_tv",
        "kernels" + "_tv",
        "lorentz" + "_tv",
        "tv" + "_backtest",
        "lc" + "_parity_mode",
        "pine" + "_exact",
    ]
    offenders: list[str] = []
    for path in _iter_text_files():
        text = path.read_text(encoding="utf-8", errors="ignore")
        for token in disallowed:
            if token in text:
                offenders.append(f"{path.relative_to(ROOT)}: {token}")

    assert offenders == []
