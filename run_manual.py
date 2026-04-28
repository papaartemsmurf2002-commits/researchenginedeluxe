from __future__ import annotations

import asyncio
import sys
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
        config = AppConfig(
            runtime_mode=RuntimeMode(sys.argv[1]),
            db_path=config.db_path,
            webhook=config.webhook,
            strategy=config.strategy,
            binance=config.binance,
            hyperliquid=config.hyperliquid,
        )
    asyncio.run(run_manual_shell(config))


if __name__ == "__main__":
    main()
