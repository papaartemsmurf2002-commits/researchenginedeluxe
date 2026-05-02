from __future__ import annotations

import sys
from pathlib import Path

import uvicorn

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tradingbotsuite.config import AppConfig
from tradingbotsuite.live.preflight import assert_live_preflight


def main() -> None:
    assert_live_preflight(AppConfig.from_env(), command="serve")
    uvicorn.run("tradingbotsuite.main:app", host="127.0.0.1", port=8000, reload=False, app_dir=str(SRC))


if __name__ == "__main__":
    main()
