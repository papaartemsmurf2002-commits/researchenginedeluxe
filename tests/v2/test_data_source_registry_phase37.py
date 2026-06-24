from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from tradingbotsuite.v2.data_sources.schemas import (
    CostClass,
    DataFamilyCoverageReport,
    MappingStatus,
    SourceRegistryEntry,
    VenueSymbolMapRow,
    require_strict_zero_dollar_source,
    require_verified_external_mapping,
)


ROOT = Path(__file__).resolve().parents[2]
CONFIG_ROOT = ROOT / "configs" / "data_sources"


def _load_json(rel_path: str) -> dict:
    return json.loads((CONFIG_ROOT / rel_path).read_text(encoding="utf-8"))


def test_source_registry_schema_files_define_required_cost_classes() -> None:
    schema = _load_json("v2_source_registry.schema.json")

    assert {
        "source_id",
        "venue",
        "market_type",
        "native_to_hyperliquid",
        "cost_class",
        "auth_required",
        "paid_required",
        "data_families",
        "history_mode",
        "priority",
        "research_role",
    }.issubset(set(schema["required"]))
    assert schema["properties"]["cost_class"]["enum"] == [
        "zero_cost_public",
        "public_rate_limited",
        "free_sample_only",
        "public_requester_pays_transfer",
        "paid_or_keyed",
    ]


def test_source_registry_sample_validates_and_strict_free_gate_passes() -> None:
    entry = SourceRegistryEntry(
        **_load_json("samples/source_registry_binance_vision_usdm_trades.json")
    )

    require_strict_zero_dollar_source(entry)
    assert entry.source_id == "binance_vision_usdm_trades"
    assert entry.native_to_hyperliquid is False
    assert entry.cost_class == CostClass.ZERO_COST_PUBLIC
    assert entry.accepted_historical_coverage_proof is True


def test_hyperliquid_public_rest_collector_sources_are_registered() -> None:
    sample_paths = {
        "hyperliquid_info_funding_history": "samples/source_registry_hyperliquid_info_funding_history.json",
        "hyperliquid_info_candle_snapshot_recent": "samples/source_registry_hyperliquid_info_candle_snapshot_recent.json",
        "hyperliquid_info_l2_book_snapshot": "samples/source_registry_hyperliquid_info_l2_book_snapshot.json",
    }

    entries = {
        source_id: SourceRegistryEntry(**_load_json(path))
        for source_id, path in sample_paths.items()
    }

    for source_id, entry in entries.items():
        require_strict_zero_dollar_source(entry)
        assert entry.source_id == source_id
        assert entry.venue == "hyperliquid"
        assert entry.native_to_hyperliquid is True
        assert entry.cost_class == CostClass.ZERO_COST_PUBLIC
        assert entry.accepted_under_strict_free is True
        assert entry.accepted_historical_coverage_proof is False
        assert entry.rate_limit_policy is not None
        assert {
            "raw_request_id",
            "raw_response_id",
            "raw_payload_sha256",
            "source_coin",
            "row_count",
            "requested_at_utc",
        }.issubset(set(entry.provenance_required))

    funding = entries["hyperliquid_info_funding_history"]
    assert funding.data_families == ("funding",)
    assert {"start_time_ms", "end_time_ms", "page_count"}.issubset(
        set(funding.provenance_required)
    )

    candles = entries["hyperliquid_info_candle_snapshot_recent"]
    assert candles.data_families == ("candles",)
    assert {"interval", "recent_window_cap"}.issubset(
        set(candles.provenance_required)
    )
    assert any("recent-window" in caveat for caveat in candles.caveats)

    l2 = entries["hyperliquid_info_l2_book_snapshot"]
    assert l2.data_families == ("bbo", "l2_order_book", "l2_snapshots")
    assert "levels_per_side_cap" in l2.provenance_required
    assert any("20 levels per side" in caveat for caveat in l2.caveats)


def test_hyperliquid_public_websocket_sources_are_registered() -> None:
    sample_paths = {
        "hyperliquid_ws_trades": "samples/source_registry_hyperliquid_ws_trades.json",
        "hyperliquid_ws_bbo": "samples/source_registry_hyperliquid_ws_bbo.json",
        "hyperliquid_ws_l2_book": "samples/source_registry_hyperliquid_ws_l2_book.json",
        "hyperliquid_ws_candle": "samples/source_registry_hyperliquid_ws_candle.json",
    }

    entries = {
        source_id: SourceRegistryEntry(**_load_json(path))
        for source_id, path in sample_paths.items()
    }

    for source_id, entry in entries.items():
        require_strict_zero_dollar_source(entry)
        assert entry.source_id == source_id
        assert entry.venue == "hyperliquid"
        assert entry.native_to_hyperliquid is True
        assert entry.cost_class == CostClass.ZERO_COST_PUBLIC
        assert entry.accepted_under_strict_free is True
        assert entry.accepted_historical_coverage_proof is False
        assert entry.history_mode == "public_websocket_bounded_capture"
        assert {
            "source_registry_source_id",
            "raw_request_id",
            "raw_response_id",
            "raw_payload_sha256",
            "source_endpoint_or_subscription",
            "message_count",
            "row_count",
            "max_messages",
            "max_rows",
            "max_seconds",
            "capture_session_id",
        }.issubset(set(entry.provenance_required))
        assert any("bounded public WebSocket" in caveat for caveat in entry.caveats)
        assert any("not continuous historical" in caveat for caveat in entry.caveats)

    assert entries["hyperliquid_ws_trades"].data_families == ("trades",)
    assert entries["hyperliquid_ws_bbo"].data_families == ("bbo",)
    assert entries["hyperliquid_ws_l2_book"].data_families == (
        "l2_order_book",
        "l2_snapshots",
    )
    assert entries["hyperliquid_ws_candle"].data_families == ("candles",)
    assert "interval" in entries["hyperliquid_ws_candle"].provenance_required


def test_bybit_okx_public_market_sources_are_external_comparison_only() -> None:
    sample_paths = {
        "bybit_public_market": "samples/source_registry_bybit_public_market.json",
        "okx_public_market": "samples/source_registry_okx_public_market.json",
    }

    for source_id, path in sample_paths.items():
        entry = SourceRegistryEntry(**_load_json(path))

        require_strict_zero_dollar_source(entry)
        assert entry.source_id == source_id
        assert entry.venue in {"bybit", "okx"}
        assert entry.native_to_hyperliquid is False
        assert entry.cost_class == CostClass.PUBLIC_RATE_LIMITED
        assert entry.accepted_under_strict_free is True
        assert entry.accepted_historical_coverage_proof is False
        assert entry.research_role == "external_comparison"
        assert {
            "candles",
            "trades",
            "bbo",
            "l2_order_book",
            "funding",
            "open_interest",
        }.issubset(set(entry.data_families))
        assert {
            "source_registry_source_id",
            "symbol_map_ref",
            "raw_request_id",
            "raw_response_id",
            "raw_payload_sha256",
            "endpoint",
            "params",
            "rate_limit_metadata",
        }.issubset(set(entry.provenance_required))
        assert any("never relabel" in caveat for caveat in entry.caveats)
        assert any("availability matrix" in caveat for caveat in entry.caveats)


def test_alt_derivatives_public_sources_are_external_comparison_only() -> None:
    sample_paths = {
        "bitget_public_mix_market": "samples/source_registry_bitget_public_mix_market.json",
        "mexc_contract_public": "samples/source_registry_mexc_contract_public.json",
        "gate_futures_public": "samples/source_registry_gate_futures_public.json",
        "kucoin_futures_public": "samples/source_registry_kucoin_futures_public.json",
        "htx_swap_public": "samples/source_registry_htx_swap_public.json",
    }

    for source_id, path in sample_paths.items():
        entry = SourceRegistryEntry(**_load_json(path))

        require_strict_zero_dollar_source(entry)
        assert entry.source_id == source_id
        assert entry.venue in {"bitget", "mexc", "gate", "kucoin", "htx"}
        assert entry.native_to_hyperliquid is False
        assert entry.cost_class == CostClass.PUBLIC_RATE_LIMITED
        assert entry.accepted_under_strict_free is True
        assert entry.accepted_historical_coverage_proof is False
        assert entry.research_role == "external_comparison"
        assert {"candles", "trades", "l2_order_book", "funding"}.issubset(
            set(entry.data_families)
        )
        assert {
            "source_registry_source_id",
            "symbol_map_ref",
            "raw_request_id",
            "raw_response_id",
            "raw_payload_sha256",
            "endpoint",
            "params",
            "rate_limit_metadata",
        }.issubset(set(entry.provenance_required))
        assert any("never relabel" in caveat for caveat in entry.caveats)
        assert any("availability matrix" in caveat for caveat in entry.caveats)


def test_dydx_deribit_reference_sources_are_external_comparison_only() -> None:
    sample_paths = {
        "dydx_indexer_public": "samples/source_registry_dydx_indexer_public.json",
        "deribit_public": "samples/source_registry_deribit_public.json",
    }

    for source_id, path in sample_paths.items():
        entry = SourceRegistryEntry(**_load_json(path))

        require_strict_zero_dollar_source(entry)
        assert entry.source_id == source_id
        assert entry.venue in {"dydx", "deribit"}
        assert entry.native_to_hyperliquid is False
        assert entry.cost_class == CostClass.PUBLIC_RATE_LIMITED
        assert entry.accepted_under_strict_free is True
        assert entry.accepted_historical_coverage_proof is False
        assert entry.research_role == "external_comparison"
        assert {"universe_metadata", "trades", "l2_order_book", "funding"}.issubset(
            set(entry.data_families)
        )
        assert {
            "source_registry_source_id",
            "symbol_map_ref",
            "raw_request_id",
            "raw_response_id",
            "raw_payload_sha256",
            "endpoint",
            "params",
            "overlap_universe_ref",
            "rate_limit_metadata",
        }.issubset(set(entry.provenance_required))
        assert any("never relabel" in caveat for caveat in entry.caveats)
        assert any("overlap" in caveat for caveat in entry.caveats)


def test_spot_oracle_context_sources_are_context_only_or_external_spot() -> None:
    sample_paths = {
        "coinbase_spot_public": "samples/source_registry_coinbase_spot_public.json",
        "kraken_spot_public": "samples/source_registry_kraken_spot_public.json",
        "pyth_hermes_public": "samples/source_registry_pyth_hermes_public.json",
        "defillama_public": "samples/source_registry_defillama_public.json",
        "dexscreener_public": "samples/source_registry_dexscreener_public.json",
        "geckoterminal_public": "samples/source_registry_geckoterminal_public.json",
    }

    for source_id, path in sample_paths.items():
        entry = SourceRegistryEntry(**_load_json(path))

        require_strict_zero_dollar_source(entry)
        assert entry.source_id == source_id
        assert entry.venue in {
            "coinbase",
            "kraken",
            "pyth",
            "defillama",
            "dexscreener",
            "geckoterminal",
        }
        assert entry.market_type in {"spot", "oracle", "context"}
        assert entry.native_to_hyperliquid is False
        assert entry.cost_class in {
            CostClass.ZERO_COST_PUBLIC,
            CostClass.PUBLIC_RATE_LIMITED,
        }
        assert entry.accepted_under_strict_free is True
        assert entry.accepted_historical_coverage_proof is False
        assert "spot_oracle_context" in entry.data_families
        assert {
            "source_registry_source_id",
            "raw_request_id",
            "raw_response_id",
            "raw_payload_sha256",
            "endpoint",
            "params",
            "row_count",
            "rate_limit_metadata",
        }.issubset(set(entry.provenance_required))
        assert any("never relabel" in caveat for caveat in entry.caveats)
        assert any("availability matrix" in caveat for caveat in entry.caveats)

        if entry.market_type == "spot":
            assert entry.research_role == "external_comparison"
            assert "symbol_map_ref" in entry.provenance_required
            assert {"candles", "trades"}.issubset(set(entry.data_families))
        else:
            assert entry.research_role == "spot_or_oracle_context"
            assert "context" in entry.history_mode
            assert any("context" in caveat for caveat in entry.caveats)


def test_requester_pays_hyperliquid_official_source_is_quarantined() -> None:
    entry = SourceRegistryEntry(
        **_load_json("samples/source_registry_hyperliquid_official_fills_quarantined.json")
    )

    assert entry.cost_class == CostClass.PUBLIC_REQUESTER_PAYS_TRANSFER
    assert entry.strict_zero_dollar_allowed is False
    assert entry.accepted_under_strict_free is False
    with pytest.raises(ValueError, match="not allowed in strict-zero-dollar mode"):
        require_strict_zero_dollar_source(entry)

    payload = entry.model_dump()
    payload["strict_zero_dollar_allowed"] = True
    with pytest.raises(ValidationError, match="cannot be strict-zero-dollar allowed"):
        SourceRegistryEntry(**payload)


def test_all_hyperliquid_official_requester_pays_sources_are_quarantined() -> None:
    sample_paths = {
        "hyperliquid_official_s3_l2_book": "samples/source_registry_hyperliquid_official_s3_l2_book.json",
        "hyperliquid_official_s3_asset_ctxs": "samples/source_registry_hyperliquid_official_s3_asset_ctxs.json",
        "hyperliquid_official_s3_node_fills_by_block": "samples/source_registry_hyperliquid_official_fills_quarantined.json",
        "hyperliquid_official_s3_node_fills": "samples/source_registry_hyperliquid_official_s3_node_fills.json",
        "hyperliquid_official_s3_node_trades": "samples/source_registry_hyperliquid_official_s3_node_trades.json",
    }

    for source_id, path in sample_paths.items():
        entry = SourceRegistryEntry(**_load_json(path))

        assert entry.source_id == source_id
        assert entry.venue == "hyperliquid"
        assert entry.native_to_hyperliquid is True
        assert entry.cost_class == CostClass.PUBLIC_REQUESTER_PAYS_TRANSFER
        assert entry.strict_zero_dollar_allowed is False
        assert entry.accepted_under_strict_free is False
        assert entry.accepted_historical_coverage_proof is False
        assert entry.required_operator_gate
        assert "coverage_audit_by_symbol_and_day" in entry.required_operator_gate
        with pytest.raises(ValueError, match="not allowed in strict-zero-dollar mode"):
            require_strict_zero_dollar_source(entry)


def test_paid_or_keyed_sources_fail_strict_free_by_default() -> None:
    payload = _load_json("samples/source_registry_binance_vision_usdm_trades.json")
    payload.update(
        {
            "source_id": "paid_vendor_export",
            "cost_class": "paid_or_keyed",
            "auth_required": True,
            "secret_required": True,
            "paid_required": True,
            "strict_zero_dollar_allowed": False,
            "accepted_under_strict_free": False,
            "accepted_historical_coverage_proof": False,
        }
    )
    entry = SourceRegistryEntry(**payload)

    with pytest.raises(ValueError, match="not allowed in strict-zero-dollar mode"):
        require_strict_zero_dollar_source(entry)


def test_free_sample_sources_cannot_claim_historical_coverage() -> None:
    payload = _load_json("samples/source_registry_binance_vision_usdm_trades.json")
    payload.update(
        {
            "source_id": "crypto_lake_free_sample",
            "venue": "crypto_lake",
            "cost_class": "free_sample_only",
            "accepted_under_strict_free": False,
            "accepted_historical_coverage_proof": True,
        }
    )

    with pytest.raises(ValidationError, match="free samples cannot prove"):
        SourceRegistryEntry(**payload)


def test_symbol_map_sample_validates_and_blocks_unverified_external_mapping() -> None:
    row = VenueSymbolMapRow(**_load_json("samples/symbol_map_sol_2026_06_22.json"))

    assert require_verified_external_mapping(row, "binance_usdm").symbol == "SOLUSDT"
    with pytest.raises(ValueError, match="okx_swap mapping is not_checked"):
        require_verified_external_mapping(row, "okx_swap")


def test_ambiguous_symbol_map_requires_blocker_reason() -> None:
    payload = _load_json("samples/symbol_map_sol_2026_06_22.json")
    payload["external_mapping_verified"] = "ambiguous"
    payload["blocker_reasons"] = []

    with pytest.raises(ValidationError, match="require blocker reasons"):
        VenueSymbolMapRow(**payload)

    payload["blocker_reasons"] = ["bybit_symbol_collision"]
    row = VenueSymbolMapRow(**payload)
    assert row.external_mapping_verified == MappingStatus.AMBIGUOUS


def test_data_family_coverage_schema_requires_boundary_flags() -> None:
    schema = _load_json("v2_data_family_coverage.schema.json")

    for field in (
        "research_only",
        "observe_only",
        "promotion_ready",
        "candidate_evidence",
        "candidate_pack_eligible",
        "live_signal",
        "paper_signal",
        "sizing_instruction",
        "order_placement_instruction",
        "runtime_mode_change",
    ):
        assert field in schema["required"]


def test_forward_hyperliquid_capture_sample_is_non_accepted_evidence() -> None:
    report = DataFamilyCoverageReport(
        **_load_json("samples/data_family_coverage_hl_btc_trades_forward_segment.json")
    )

    assert report.accepted_for_research_reporting is False
    assert "forward_capture_segment_only" in report.reason
    assert report.research_only is True
    assert report.promotion_ready is False


def test_coverage_acceptance_rejects_forward_proxy_and_bad_boundary() -> None:
    payload = _accepted_coverage_payload()
    DataFamilyCoverageReport(**payload)

    payload_with_reason = dict(payload)
    payload_with_reason["reason"] = ["forward_capture_segment_only"]
    with pytest.raises(ValidationError, match="cannot carry blocker reasons"):
        DataFamilyCoverageReport(**payload_with_reason)

    proxy_payload = dict(payload)
    proxy_payload["labels"] = ["external_proxy"]
    with pytest.raises(ValidationError, match="external proxy coverage cannot be accepted"):
        DataFamilyCoverageReport(**proxy_payload)

    paid_payload = dict(payload)
    paid_payload["source_cost_classes"] = ["paid_or_keyed"]
    with pytest.raises(ValidationError, match="diagnostic or paid sources"):
        DataFamilyCoverageReport(**paid_payload)

    boundary_payload = dict(payload)
    boundary_payload["live_signal"] = True
    with pytest.raises(ValidationError, match="violates v2 research boundary"):
        DataFamilyCoverageReport(**boundary_payload)


def _accepted_coverage_payload() -> dict:
    return {
        "manifest_type": "data_family_coverage_report",
        "coverage_report_id": "hl-btc-funding-accepted-smoke",
        "universe_snapshot_ref": "manifests/universe/hyperliquid_asof_2026-06-22.json",
        "source_registry_ref": "manifests/source_registry/source_registry_v1.json",
        "symbol_map_ref": "manifests/symbol_maps/symbol_map_2026-06-22.json",
        "archive_snapshot_ref": "manifests/archive_snapshots/snapshot.json",
        "symbol": "BTC",
        "family": "funding",
        "venue": "hyperliquid",
        "source_ids": ["hyperliquid_info_funding_history"],
        "source_cost_classes": ["zero_cost_public"],
        "labels": ["native_hyperliquid"],
        "coverage_window": {
            "start": datetime(2024, 1, 1, tzinfo=UTC).isoformat(),
            "end": datetime(2024, 7, 1, tzinfo=UTC).isoformat(),
        },
        "expected_buckets": {"bucket_seconds": 3600, "count": 4368},
        "observed_buckets": 4368,
        "coverage_ratio": 1.0,
        "accepted_for_research_reporting": True,
        "reason": [],
        "research_only": True,
        "observe_only": True,
        "promotion_ready": False,
        "candidate_evidence": False,
        "candidate_pack_eligible": False,
        "live_signal": False,
        "paper_signal": False,
        "sizing_instruction": False,
        "order_placement_instruction": False,
        "runtime_mode_change": False,
    }
