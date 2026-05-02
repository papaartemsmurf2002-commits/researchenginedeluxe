from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tradingbotsuite.config import AppConfig
from tradingbotsuite.live.preflight import assert_live_preflight
from tradingbotsuite.main import _config_with_runtime_mode
from tradingbotsuite.manual_cli import run_manual_shell


def main() -> None:
    config = AppConfig.from_env()
    if len(sys.argv) > 1:
        config = _config_with_runtime_mode(config, sys.argv[1])
    assert_live_preflight(config, command="manual")
    asyncio.run(run_manual_shell(config))


if __name__ == "__main__":
    main()
