from __future__ import annotations

from decimal import Decimal

import pytest

from tradingbotsuite.config import AppConfig, BinanceConfig, StrategyConfig


def test_strategy_config_normalizes_and_includes_primary_microstructure_window() -> None:
    config = StrategyConfig(
        microstructure_primary_window_seconds=20,
        microstructure_windows_seconds=(60, 10, 20, 10, 30),
    )

    assert config.microstructure_windows_seconds == (10, 20, 30, 60)


def test_strategy_config_rejects_invalid_positive_constraints() -> None:
    with pytest.raises(ValueError, match="order size must be positive"):
        StrategyConfig(order_size=Decimal("0"))

    with pytest.raises(ValueError, match="price tick and size step must be positive"):
        StrategyConfig(price_tick=Decimal("0"))


def test_binance_config_rejects_invalid_depth_settings() -> None:
    with pytest.raises(ValueError, match="depth update speed"):
        BinanceConfig(depth_update_speed_ms=0)

    with pytest.raises(ValueError, match="depth snapshot limit"):
        BinanceConfig(depth_snapshot_limit=0)


def test_app_config_loads_hyperliquid_testnet_file_without_enabling_live_when_env_missing(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("TBS_HL_BASE_URL", raising=False)
    monkeypatch.delenv("TBS_HL_PRIVATE_KEY", raising=False)
    monkeypatch.delenv("TBS_HL_ACCOUNT_ADDRESS", raising=False)
    monkeypatch.delenv("TBS_HL_ENABLE_LIVE", raising=False)
    (tmp_path / "hyperliquidtestnet.txt").write_text(
        "\n".join(
            [
                "testnet",
                "0x1111111111111111111111111111111111111111111111111111111111111111 private",
                "0x2222222222222222222222222222222222222222 adress",
                "main adress",
                "0x3333333333333333333333333333333333333333",
            ]
        ),
        encoding="utf-8",
    )

    config = AppConfig.from_env()

    assert config.hyperliquid.base_url == "https://api.hyperliquid-testnet.xyz"
    assert config.hyperliquid.enable_live is False
    assert config.hyperliquid.private_key == "0x1111111111111111111111111111111111111111111111111111111111111111"
    assert config.hyperliquid.account_address == "0x3333333333333333333333333333333333333333"


def test_app_config_requires_explicit_live_enable_even_with_hyperliquid_testnet_file(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("TBS_HL_BASE_URL", raising=False)
    monkeypatch.delenv("TBS_HL_PRIVATE_KEY", raising=False)
    monkeypatch.delenv("TBS_HL_ACCOUNT_ADDRESS", raising=False)
    monkeypatch.setenv("TBS_HL_ENABLE_LIVE", "true")
    (tmp_path / "hyperliquidtestnet.txt").write_text(
        "\n".join(
            [
                "testnet",
                "0x1111111111111111111111111111111111111111111111111111111111111111 private",
                "0x2222222222222222222222222222222222222222 adress",
            ]
        ),
        encoding="utf-8",
    )

    config = AppConfig.from_env()

    assert config.hyperliquid.base_url == "https://api.hyperliquid-testnet.xyz"
    assert config.hyperliquid.enable_live is True
    assert config.hyperliquid.private_key == "0x1111111111111111111111111111111111111111111111111111111111111111"
    assert config.hyperliquid.account_address == "0x2222222222222222222222222222222222222222"


def test_app_config_explicit_mainnet_url_with_file_credentials_still_requires_live_enable(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("TBS_HL_BASE_URL", "https://api.hyperliquid.xyz")
    monkeypatch.delenv("TBS_HL_PRIVATE_KEY", raising=False)
    monkeypatch.delenv("TBS_HL_ACCOUNT_ADDRESS", raising=False)
    monkeypatch.delenv("TBS_HL_ENABLE_LIVE", raising=False)
    (tmp_path / "hyperliquidtestnet.txt").write_text(
        "\n".join(
            [
                "testnet",
                "0x1111111111111111111111111111111111111111111111111111111111111111 private",
                "0x2222222222222222222222222222222222222222 adress",
            ]
        ),
        encoding="utf-8",
    )

    config = AppConfig.from_env()

    assert config.hyperliquid.base_url == "https://api.hyperliquid.xyz"
    assert config.hyperliquid.enable_live is False
    assert config.hyperliquid.private_key == "0x1111111111111111111111111111111111111111111111111111111111111111"
    assert config.hyperliquid.account_address == "0x2222222222222222222222222222222222222222"


def test_app_config_prefers_explicit_hyperliquid_env_over_testnet_file(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "hyperliquidtestnet.txt").write_text(
        "testnet\n0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa private\n0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb adress\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("TBS_HL_BASE_URL", "https://api.hyperliquid.xyz")
    monkeypatch.setenv("TBS_HL_PRIVATE_KEY", "0xcccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc")
    monkeypatch.setenv("TBS_HL_ACCOUNT_ADDRESS", "0xdddddddddddddddddddddddddddddddddddddddd")
    monkeypatch.setenv("TBS_HL_ENABLE_LIVE", "false")

    config = AppConfig.from_env()

    assert config.hyperliquid.base_url == "https://api.hyperliquid.xyz"
    assert config.hyperliquid.enable_live is False
    assert config.hyperliquid.private_key == "0xcccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"
    assert config.hyperliquid.account_address == "0xdddddddddddddddddddddddddddddddddddddddd"
