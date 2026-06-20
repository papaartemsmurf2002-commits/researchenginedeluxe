from __future__ import annotations

RESEARCH_COMMANDS = frozenset(
    {
        "benchmark-research-experiment",
        "audit-rapid-strategy-sandbox-archives",
        "benchmark-discovery-run",
        "benchmark-hardware-utilization",
        "benchmark-historical-research-cycle",
        "build-four-bar-knn-dataset",
        "build-historical-fixture-pack",
        "build-rapid-strategy-sandbox-archive-manifest",
        "build-rapid-strategy-sandbox-strategy-catalog",
        "collect-durable-data",
        "build-dataset",
        "calibrate-model",
        "collect-binance-bars",
        "collect-binance-context",
        "evaluate-discovery-candidate-pack-eligibility",
        "export-rapid-strategy-sandbox-venue-expansion-candidate-manifest",
        "export-rapid-strategy-sandbox-venue-expansion-requests",
        "export-rapid-strategy-sandbox-validation-requests",
        "fetch-binance-vision",
        "fetch-crypto-lake",
        "index-rapid-strategy-sandbox-artifacts",
        "index-rapid-strategy-sandbox-iterations",
        "materialize-rapid-strategy-sandbox-venue-expansion-requests",
        "map-binance-archive-four-bar-datasets",
        "monitor-hmm-knn",
        "plan-feature-ablation",
        "plan-stage12-research",
        "plan-stage13-readiness",
        "preflight-rapid-strategy-sandbox",
        "preflight-rapid-strategy-sandbox-validation-requests",
        "prepare-hmm-knn-research-data",
        "rank-rapid-strategy-sandbox-artifacts",
        "refresh-historical-data-catalog",
        "replay-eval",
        "replay-hmm-knn",
        "research",
        "research-hmm-knn",
        "run-discovery",
        "run-four-bar-knn-larger-validation",
        "run-hmm-knn-experiments",
        "run-historical-research-cycle",
        "run-rapid-strategy-sandbox",
        "run-rapid-strategy-sandbox-iteration",
        "run-rapid-strategy-sandbox-suite",
        "run-research-experiment",
        "show-rapid-strategy-sandbox-next-action",
        "summarize-rapid-strategy-sandbox-archive-coverage",
        "summarize-rapid-strategy-sandbox-hypotheses",
        "summarize-rapid-strategy-sandbox",
        "summarize-rapid-strategy-sandbox-throughput",
        "train-model",
        "verify-rapid-strategy-sandbox-artifacts",
        "write-hmm-knn-sweep-datasets",
    }
)


def normalize_command_name(command: str | None) -> str:
    return str(command or "").strip().lower()


def is_research_command(command: str | None) -> bool:
    return normalize_command_name(command) in RESEARCH_COMMANDS
