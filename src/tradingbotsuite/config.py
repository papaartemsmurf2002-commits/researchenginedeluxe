from __future__ import annotations

import os
import re
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from tradingbotsuite.core.models import RuntimeMode

HEX_40_OR_64_RE = re.compile(r"0x[a-fA-F0-9]{40,64}")


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _resolve_hyperliquid_testnet_file() -> Path | None:
    explicit = os.getenv("TBS_HL_TESTNET_FILE")
    candidates: list[Path] = []
    if explicit:
        candidates.append(Path(explicit).expanduser())
    candidates.extend(
        [
            Path.cwd() / "hyperliquidtestnet.txt",
            _repo_root() / "hyperliquidtestnet.txt",
        ]
    )
    seen: set[Path] = set()
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        if resolved.exists() and resolved.is_file():
            return resolved
    return None


def _load_hyperliquid_testnet_credentials() -> dict[str, str | bool] | None:
    path = _resolve_hyperliquid_testnet_file()
    if path is None:
        return None
    lines = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not lines:
        return None

    network = "testnet" if any("testnet" in line.lower() for line in lines[:2]) else None
    private_key: str | None = None
    primary_address: str | None = None
    main_address: str | None = None
    pending_main_label = False

    for line in lines:
        lowered = line.lower()
        matches = HEX_40_OR_64_RE.findall(line)
        key_match = next((match for match in matches if len(match) == 66), None)
        address_matches = [match for match in matches if len(match) == 42]
        if key_match and private_key is None:
            private_key = key_match
        if "main" in lowered and ("address" in lowered or "adress" in lowered):
            pending_main_label = True
            if address_matches and main_address is None:
                main_address = address_matches[0]
                pending_main_label = False
        elif pending_main_label and address_matches and main_address is None:
            main_address = address_matches[0]
            pending_main_label = False
        if address_matches and primary_address is None:
            primary_address = address_matches[0]

    account_address = main_address or primary_address
    if private_key is None or account_address is None:
        return None

    payload: dict[str, str | bool] = {
        "private_key": private_key,
        "account_address": account_address,
        "source_path": str(path),
    }
    if network == "testnet":
        payload["base_url"] = "https://api.hyperliquid-testnet.xyz"
    return payload


@dataclass(frozen=True, slots=True)
class WebhookConfig:
    secret: str = "change-me"
    timestamp_tolerance_seconds: int = 120

    def __post_init__(self) -> None:
        if self.timestamp_tolerance_seconds <= 0:
            raise ValueError("webhook timestamp tolerance must be positive")


@dataclass(frozen=True, slots=True)
class StrategyConfig:
    atr_length: int = 14
    hurst_window_bars: int = 256
    take_profit_atr_multiple: Decimal = Decimal("1.5")
    stop_loss_atr_multiple: Decimal = Decimal("1.0")
    time_barrier_bars: int = 24
    order_size: Decimal = Decimal("0.001")
    entry_slippage_bps: Decimal = Decimal("5")
    exit_slippage_bps: Decimal = Decimal("5")
    microstructure_primary_window_seconds: int = 20
    microstructure_windows_seconds: tuple[int, ...] = (10, 20, 30, 60)
    signed_imbalance_ratio_threshold: Decimal = Decimal("0")
    book_imbalance_ratio_threshold: Decimal = Decimal("0")
    price_tick: Decimal = Decimal("0.1")
    size_step: Decimal = Decimal("0.001")
    stale_bar_after_ms: int = 20 * 60 * 1000
    stale_trade_after_ms: int = 120_000
    stale_book_ticker_after_ms: int = 120_000
    stale_depth_after_ms: int = 120_000
    max_reconcile_gap_ms: int = 60_000
    max_spread_bps: Decimal = Decimal("25")
    max_daily_loss_quote: Decimal = Decimal("0")
    max_open_risk_notional: Decimal = Decimal("0")

    def __post_init__(self) -> None:
        if self.atr_length <= 0:
            raise ValueError("ATR length must be positive")
        if self.hurst_window_bars < 32:
            raise ValueError("Hurst window must be at least 32 bars")
        if self.take_profit_atr_multiple <= 0 or self.stop_loss_atr_multiple <= 0:
            raise ValueError("ATR barrier multiples must be positive")
        if self.time_barrier_bars <= 0:
            raise ValueError("time barrier bars must be positive")
        if self.order_size <= 0:
            raise ValueError("order size must be positive")
        if self.entry_slippage_bps < 0 or self.exit_slippage_bps < 0:
            raise ValueError("slippage bps must be non-negative")
        if self.microstructure_primary_window_seconds <= 0:
            raise ValueError("primary microstructure window must be positive")
        normalized_windows = tuple(
            sorted(
                {
                    int(window_seconds)
                    for window_seconds in self.microstructure_windows_seconds
                    if int(window_seconds) > 0
                }
                | {self.microstructure_primary_window_seconds}
            )
        )
        if not normalized_windows:
            raise ValueError("at least one positive microstructure window is required")
        object.__setattr__(self, "microstructure_windows_seconds", normalized_windows)
        if self.price_tick <= 0 or self.size_step <= 0:
            raise ValueError("price tick and size step must be positive")
        if (
            self.stale_bar_after_ms <= 0
            or self.stale_trade_after_ms <= 0
            or self.stale_book_ticker_after_ms <= 0
            or self.stale_depth_after_ms <= 0
            or self.max_reconcile_gap_ms <= 0
        ):
            raise ValueError("staleness and reconcile windows must be positive")
        if self.max_spread_bps < 0 or self.max_daily_loss_quote < 0 or self.max_open_risk_notional < 0:
            raise ValueError("spread and risk limits must be non-negative")


@dataclass(frozen=True, slots=True)
class BinanceConfig:
    base_url: str = "https://fapi.binance.com"
    ws_base_url: str = "wss://fstream.binance.com"
    kline_limit_padding: int = 5
    ws_stale_after_ms: int = 120_000
    depth_update_speed_ms: int = 250
    depth_snapshot_limit: int = 1000
    depth_required_levels: int = 10
    depth_resync_min_interval_ms: int = 2_000
    depth_snapshot_default_backoff_ms: int = 15_000
    depth_max_buffer_events: int = 8_192
    depth_reconnect_backoff_ms: int = 1_000
    depth_reconnect_max_backoff_ms: int = 30_000
    websocket_planned_reconnect_ms: int = 85_500_000
    websocket_planned_reconnect_jitter_ms: int = 60_000
    rest_weight_budget_pct: float = 0.85
    market_streams_enabled: bool = True

    def __post_init__(self) -> None:
        if self.kline_limit_padding < 0:
            raise ValueError("Binance kline limit padding must be non-negative")
        if self.ws_stale_after_ms <= 0:
            raise ValueError("Binance websocket stale timeout must be positive")
        if self.depth_update_speed_ms <= 0:
            raise ValueError("Binance depth update speed must be positive")
        if self.depth_snapshot_limit <= 0 or self.depth_snapshot_limit > 1000:
            raise ValueError("Binance depth snapshot limit must be between 1 and 1000")
        if self.depth_required_levels <= 0 or self.depth_required_levels > self.depth_snapshot_limit:
            raise ValueError("Binance depth required levels must be positive and no larger than the snapshot limit")
        if self.depth_resync_min_interval_ms < 0 or self.depth_snapshot_default_backoff_ms <= 0:
            raise ValueError("Binance depth cooldown and backoff must be positive")
        if self.depth_max_buffer_events <= 0:
            raise ValueError("Binance depth max buffer events must be positive")
        if self.depth_reconnect_backoff_ms < 0 or self.depth_reconnect_max_backoff_ms < self.depth_reconnect_backoff_ms:
            raise ValueError("Binance reconnect backoff settings must be non-negative and ordered")
        if self.websocket_planned_reconnect_ms <= 0 or self.websocket_planned_reconnect_jitter_ms < 0:
            raise ValueError("Binance websocket planned reconnect settings must be positive")
        if self.rest_weight_budget_pct <= 0 or self.rest_weight_budget_pct > 1:
            raise ValueError("Binance REST budget pct must be between 0 and 1")


@dataclass(frozen=True, slots=True)
class HyperliquidConfig:
    base_url: str = "https://api.hyperliquid.xyz"
    account_address: str | None = None
    private_key: str | None = None
    vault_address: str | None = None
    enable_live: bool = False
    market_order_slippage: float = 0.03
    order_timeout_seconds: int = 5
    ws_stale_after_ms: int = 120_000
    max_basis_bps: Decimal = Decimal("75")

    def __post_init__(self) -> None:
        if self.market_order_slippage < 0:
            raise ValueError("Hyperliquid market order slippage must be non-negative")
        if self.order_timeout_seconds <= 0 or self.ws_stale_after_ms <= 0:
            raise ValueError("Hyperliquid timeouts must be positive")
        if self.max_basis_bps < 0:
            raise ValueError("Hyperliquid max basis bps must be non-negative")


@dataclass(frozen=True, slots=True)
class ResearchConfig:
    output_dir: Path = Path("data/research")
    config_path: Path = Path("configs/v2_btc_research.json")
    artifact_manifest_path: Path | None = None

    def __post_init__(self) -> None:
        if str(self.output_dir).strip() == "":
            raise ValueError("research output directory must not be empty")
        if str(self.config_path).strip() == "":
            raise ValueError("research config path must not be empty")
        if self.artifact_manifest_path is not None and str(self.artifact_manifest_path).strip() == "":
            raise ValueError("research artifact manifest path must not be empty")


@dataclass(frozen=True, slots=True)
class OperatorUIConfig:
    enabled: bool = False
    secret: str | None = None
    session_cookie_name: str = "tbs_operator_session"

    def __post_init__(self) -> None:
        if self.enabled and (self.secret is None or self.secret.strip() == ""):
            raise ValueError("operator ui secret is required when ui is enabled")
        if self.session_cookie_name.strip() == "":
            raise ValueError("operator ui session cookie name must not be empty")


@dataclass(frozen=True, slots=True)
class AppConfig:
    runtime_mode: RuntimeMode = RuntimeMode.PAPER
    db_path: Path = Path("data/tradingbotsuite.sqlite3")
    webhook: WebhookConfig = WebhookConfig()
    strategy: StrategyConfig = StrategyConfig()
    binance: BinanceConfig = BinanceConfig()
    hyperliquid: HyperliquidConfig = HyperliquidConfig()
    research: ResearchConfig = ResearchConfig()
    operator_ui: OperatorUIConfig = OperatorUIConfig()

    def __post_init__(self) -> None:
        if str(self.db_path).strip() == "":
            raise ValueError("database path must not be empty")

    @classmethod
    def from_env(cls) -> "AppConfig":
        mode = RuntimeMode(os.getenv("TBS_RUNTIME_MODE", RuntimeMode.PAPER.value))
        file_credentials = _load_hyperliquid_testnet_credentials()
        db_path = Path(os.getenv("TBS_DB_PATH", "data/tradingbotsuite.sqlite3"))
        webhook = WebhookConfig(
            secret=os.getenv("TBS_WEBHOOK_SECRET", "change-me"),
            timestamp_tolerance_seconds=int(os.getenv("TBS_WEBHOOK_TOLERANCE_SECONDS", "120")),
        )
        strategy = StrategyConfig(
            atr_length=int(os.getenv("TBS_ATR_LENGTH", "14")),
            hurst_window_bars=int(os.getenv("TBS_HURST_WINDOW_BARS", "256")),
            take_profit_atr_multiple=Decimal(os.getenv("TBS_TP_ATR_MULT", "1.5")),
            stop_loss_atr_multiple=Decimal(os.getenv("TBS_SL_ATR_MULT", "1.0")),
            time_barrier_bars=int(os.getenv("TBS_TIME_BARRIER_BARS", "24")),
            order_size=Decimal(os.getenv("TBS_ORDER_SIZE", "0.001")),
            entry_slippage_bps=Decimal(os.getenv("TBS_ENTRY_SLIPPAGE_BPS", "5")),
            exit_slippage_bps=Decimal(os.getenv("TBS_EXIT_SLIPPAGE_BPS", "5")),
            microstructure_primary_window_seconds=int(os.getenv("TBS_MICRO_PRIMARY_WINDOW_SECONDS", "20")),
            microstructure_windows_seconds=tuple(
                int(part.strip())
                for part in os.getenv("TBS_MICRO_WINDOWS_SECONDS", "10,20,30,60").split(",")
                if part.strip()
            ),
            signed_imbalance_ratio_threshold=Decimal(os.getenv("TBS_SIGNED_IMBALANCE_RATIO_THRESHOLD", "0")),
            book_imbalance_ratio_threshold=Decimal(os.getenv("TBS_BOOK_IMBALANCE_RATIO_THRESHOLD", "0")),
            price_tick=Decimal(os.getenv("TBS_PRICE_TICK", "0.1")),
            size_step=Decimal(os.getenv("TBS_SIZE_STEP", "0.001")),
            stale_bar_after_ms=int(os.getenv("TBS_STALE_BAR_AFTER_MS", str(20 * 60 * 1000))),
            stale_trade_after_ms=int(os.getenv("TBS_STALE_TRADE_AFTER_MS", "120000")),
            stale_book_ticker_after_ms=int(os.getenv("TBS_STALE_BOOK_TICKER_AFTER_MS", "120000")),
            stale_depth_after_ms=int(os.getenv("TBS_STALE_DEPTH_AFTER_MS", "120000")),
            max_reconcile_gap_ms=int(os.getenv("TBS_MAX_RECONCILE_GAP_MS", "60000")),
            max_spread_bps=Decimal(os.getenv("TBS_MAX_SPREAD_BPS", "25")),
            max_daily_loss_quote=Decimal(os.getenv("TBS_MAX_DAILY_LOSS_QUOTE", "0")),
            max_open_risk_notional=Decimal(os.getenv("TBS_MAX_OPEN_RISK_NOTIONAL", "0")),
        )
        binance = BinanceConfig(
            base_url=os.getenv("TBS_BINANCE_BASE_URL", "https://fapi.binance.com"),
            ws_base_url=os.getenv("TBS_BINANCE_WS_BASE_URL", "wss://fstream.binance.com"),
            kline_limit_padding=int(os.getenv("TBS_BINANCE_KLINE_LIMIT_PADDING", "5")),
            ws_stale_after_ms=int(os.getenv("TBS_BINANCE_WS_STALE_AFTER_MS", "120000")),
            depth_update_speed_ms=int(os.getenv("TBS_BINANCE_DEPTH_UPDATE_SPEED_MS", "250")),
            depth_snapshot_limit=int(os.getenv("TBS_BINANCE_DEPTH_SNAPSHOT_LIMIT", "1000")),
            depth_required_levels=int(os.getenv("TBS_BINANCE_DEPTH_REQUIRED_LEVELS", "10")),
            depth_resync_min_interval_ms=int(
                os.getenv("TBS_BINANCE_DEPTH_RESYNC_MIN_INTERVAL_MS", os.getenv("TBS_BINANCE_DEPTH_RESYNC_COOLDOWN_MS", "2000"))
            ),
            depth_snapshot_default_backoff_ms=int(os.getenv("TBS_BINANCE_DEPTH_SNAPSHOT_DEFAULT_BACKOFF_MS", "15000")),
            depth_max_buffer_events=int(os.getenv("TBS_BINANCE_DEPTH_MAX_BUFFER_EVENTS", "8192")),
            depth_reconnect_backoff_ms=int(os.getenv("TBS_BINANCE_DEPTH_RECONNECT_BACKOFF_MS", "1000")),
            depth_reconnect_max_backoff_ms=int(os.getenv("TBS_BINANCE_DEPTH_RECONNECT_MAX_BACKOFF_MS", "30000")),
            websocket_planned_reconnect_ms=int(os.getenv("TBS_BINANCE_WS_PLANNED_RECONNECT_MS", "85500000")),
            websocket_planned_reconnect_jitter_ms=int(os.getenv("TBS_BINANCE_WS_PLANNED_RECONNECT_JITTER_MS", "60000")),
            rest_weight_budget_pct=float(os.getenv("TBS_BINANCE_REST_WEIGHT_BUDGET_PCT", "0.85")),
            market_streams_enabled=_env_bool("TBS_BINANCE_MARKET_STREAMS_ENABLED", True),
        )
        hl_base_url = os.getenv("TBS_HL_BASE_URL")
        hl_account_address = os.getenv("TBS_HL_ACCOUNT_ADDRESS")
        hl_private_key = os.getenv("TBS_HL_PRIVATE_KEY")
        hl_vault_address = os.getenv("TBS_HL_VAULT_ADDRESS")
        hyperliquid = HyperliquidConfig(
            base_url=(
                hl_base_url
                or str((file_credentials or {}).get("base_url") or "https://api.hyperliquid.xyz")
            ),
            account_address=hl_account_address or (str((file_credentials or {}).get("account_address")) if file_credentials else None),
            private_key=hl_private_key or (str((file_credentials or {}).get("private_key")) if file_credentials else None),
            vault_address=hl_vault_address,
            enable_live=_env_bool("TBS_HL_ENABLE_LIVE", False),
            market_order_slippage=float(os.getenv("TBS_HL_MARKET_SLIPPAGE", "0.03")),
            order_timeout_seconds=int(os.getenv("TBS_HL_ORDER_TIMEOUT_SECONDS", "5")),
            ws_stale_after_ms=int(os.getenv("TBS_HL_WS_STALE_AFTER_MS", "120000")),
            max_basis_bps=Decimal(os.getenv("TBS_HL_MAX_BASIS_BPS", "75")),
        )
        research = ResearchConfig(
            output_dir=Path(os.getenv("TBS_RESEARCH_OUTPUT_DIR", "data/research")),
            config_path=Path(os.getenv("TBS_RESEARCH_CONFIG_PATH", "configs/v2_btc_research.json")),
            artifact_manifest_path=(
                Path(os.getenv("TBS_RESEARCH_ARTIFACT_MANIFEST_PATH"))
                if os.getenv("TBS_RESEARCH_ARTIFACT_MANIFEST_PATH")
                else None
            ),
        )
        operator_ui = OperatorUIConfig(
            enabled=_env_bool("TBS_OPERATOR_UI_ENABLED", False),
            secret=os.getenv("TBS_OPERATOR_UI_SECRET"),
            session_cookie_name=os.getenv("TBS_OPERATOR_UI_COOKIE_NAME", "tbs_operator_session"),
        )
        return cls(
            runtime_mode=mode,
            db_path=db_path,
            webhook=webhook,
            strategy=strategy,
            binance=binance,
            hyperliquid=hyperliquid,
            research=research,
            operator_ui=operator_ui,
        )
