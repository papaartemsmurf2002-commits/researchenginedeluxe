from __future__ import annotations

import asyncio
import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tradingbotsuite.config import AppConfig
from tradingbotsuite.core.models import RuntimeMode
from tradingbotsuite.manual_cli import run_manual_shell


def main() -> None:
    config = AppConfig.from_env()
    if len(sys.argv) > 1:
        config = replace(config, runtime_mode=RuntimeMode(sys.argv[1]))
    asyncio.run(run_manual_shell(config))


if __name__ == "__main__":
    main()
