from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

REQUIRED_DOCS_WITH_SCHEMA_NAMES = {
    "docs/contracts/archive_contract.md": ("ArchiveConfig", "ArchiveLayer"),
    "docs/contracts/audit_report_contract.md": ("AuditBlockerReport", "AuditJobSummary", "AuditReportStatus"),
    "docs/contracts/universe_contract.md": ("UniverseConfig", "UniverseMode"),
    "docs/contracts/venue_adapter_contract.md": ("VenueAdapterCapability",),
    "docs/contracts/collector_job_contract.md": ("CollectorJobRecord",),
    "docs/contracts/data_quality_contract.md": ("CoverageReport",),
    "docs/contracts/backtest_data_service_contract.md": (
        "BacktestDataRequest",
        "LockboxPolicy",
        "ValidationConfig",
    ),
    "docs/contracts/strategy_spec_contract.md": ("StrategySpec",),
    "docs/contracts/strategy_plugin_contract.md": ("StrategyPluginProtocol",),
    "docs/contracts/backtest_engine_contract.md": ("BacktestRunConfig", "RunManifest"),
    "docs/contracts/cost_model_contract.md": ("CostModelConfig",),
    "docs/contracts/run_artifact_contract.md": ("RunManifest",),
    "docs/contracts/ledger_contract.md": ("LedgerRow", "LedgerAppendRequest", "LeaderboardRow"),
    "docs/contracts/lead_book_contract.md": ("LeadBookRow", "LeadState", "LeadGateResult"),
    "docs/contracts/validation_contract.md": (
        "ValidationConfig",
        "LockboxPolicy",
        "WalkForwardConfig",
        "TrialFamilyReport",
    ),
    "docs/contracts/worker_job_contract.md": ("WorkerJobRecord",),
    "docs/contracts/security_boundary_contract.md": (
        "PathPolicy",
        "SecretPolicy",
        "TrustedArtifactRef",
        "CommandClassification",
    ),
    "docs/contracts/ui_visibility_contract.md": ("V2VisibilitySnapshot",),
    "docs/V2_LEGACY_CLASSIFICATION.md": ("LegacyAuditRecord",),
}

REQUIRED_CONTRACT_TERMS = (
    "research",
    "Forbidden",
)


def test_v2_contract_docs_exist_and_name_initial_schemas() -> None:
    missing: list[str] = []
    for rel_path, schema_names in REQUIRED_DOCS_WITH_SCHEMA_NAMES.items():
        path = ROOT / rel_path
        if not path.exists():
            missing.append(f"{rel_path} missing")
            continue
        text = path.read_text(encoding="utf-8")
        for schema_name in schema_names:
            if schema_name not in text:
                missing.append(f"{rel_path} missing schema name {schema_name}")

    assert missing == []


def test_v2_contract_docs_state_boundary_or_forbidden_behavior() -> None:
    weak_docs: list[str] = []
    for rel_path in REQUIRED_DOCS_WITH_SCHEMA_NAMES:
        text = (ROOT / rel_path).read_text(encoding="utf-8")
        if not any(term in text for term in REQUIRED_CONTRACT_TERMS):
            weak_docs.append(rel_path)

    assert weak_docs == []
