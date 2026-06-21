from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
AUDIT_PATH = ROOT / "docs" / "V2_LEGACY_SUBSYSTEM_AUDIT.md"
CLASSIFICATION_PATH = ROOT / "docs" / "V2_LEGACY_CLASSIFICATION.md"
NO_TOUCH_PATH = ROOT / "docs" / "V2_NO_TOUCH_PATHS.md"

REQUIRED_SUBSYSTEMS = (
    "strict_research_cycle",
    "candidate_pack_gates",
    "rapid_sandbox",
    "old_high_return_outputs",
    "rejected_rows",
    "strategy_plugins",
    "feature_builders",
    "existing_backtest_engines",
    "legacy_gui",
    "live_runtime_adjacent_code",
    "old_tradingbot_package",
)

REQUIRED_LABELS = (
    "reuse_as_is",
    "reuse_after_fix",
    "wrap_into_v2",
    "migrate_into_v2",
    "freeze_drawer",
    "move_to_legacy_area",
    "no_touch_without_scope",
    "remove_later",
)


def test_legacy_audit_contains_required_subsystems() -> None:
    text = AUDIT_PATH.read_text(encoding="utf-8")
    missing = [subsystem for subsystem in REQUIRED_SUBSYSTEMS if f"subsystem: {subsystem}" not in text]
    assert missing == []


def test_legacy_audit_records_have_required_fields() -> None:
    text = AUDIT_PATH.read_text(encoding="utf-8")
    required_fields = (
        "files_reviewed:",
        "current_purpose:",
        "v2_usefulness:",
        "risks_found:",
        "recommended_action:",
        "required_fixes:",
        "audit_id: V2-AUD-LEGACY-001",
        "final_status: accepted",
    )
    missing = [field for field in required_fields if field not in text]
    assert missing == []


def test_legacy_classification_labels_match_roadmap() -> None:
    text = CLASSIFICATION_PATH.read_text(encoding="utf-8")
    missing = [label for label in REQUIRED_LABELS if f"`{label}`" not in text]
    assert missing == []


def test_legacy_gui_and_live_runtime_are_not_default_v2_paths() -> None:
    text = AUDIT_PATH.read_text(encoding="utf-8")
    assert "subsystem: legacy_gui" in text
    assert "recommended_action: freeze_drawer" in text
    assert "subsystem: live_runtime_adjacent_code" in text
    assert "recommended_action: no_touch_without_scope" in text


def test_old_outputs_are_preserved_sources_not_rewritten() -> None:
    audit_text = AUDIT_PATH.read_text(encoding="utf-8")
    no_touch_text = NO_TOUCH_PATH.read_text(encoding="utf-8")

    assert "subsystem: old_high_return_outputs" in audit_text
    assert "recommended_action: freeze_drawer" in audit_text
    assert "Preserve as Lead Book or negative-control sources only" in no_touch_text
    assert "do not rewrite during v2 migration" in no_touch_text
