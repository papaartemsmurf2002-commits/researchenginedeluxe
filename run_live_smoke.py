from __future__ import annotations

import asyncio
import json
import sys
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tradingbotsuite.config import AppConfig
from tradingbotsuite.live_smoke import run_live_smoke


def main() -> None:
    config = AppConfig.from_env()
    size = Decimal(sys.argv[1]) if len(sys.argv) > 1 else None
    result = asyncio.run(run_live_smoke(config, size=size))
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
