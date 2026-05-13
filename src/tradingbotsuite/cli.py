from __future__ import annotations

import runpy
from pathlib import Path


def main() -> None:
    """Console-script entrypoint for the canonical tradingbotsuite CLI."""
    runpy.run_path(str(Path(__file__).with_name("main.py")), run_name="__main__")
