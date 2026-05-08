from __future__ import annotations

RESEARCH_COMMANDS = frozenset(
    {
        "benchmark-research-experiment",
        "benchmark-discovery-run",
        "benchmark-historical-research-cycle",
        "build-historical-fixture-pack",
        "build-dataset",
        "calibrate-model",
        "collect-binance-bars",
        "collect-binance-context",
        "evaluate-discovery-candidate-pack-eligibility",
        "fetch-binance-vision",
        "fetch-crypto-lake",
        "monitor-hmm-knn",
        "plan-feature-ablation",
        "plan-stage12-research",
        "plan-stage13-readiness",
        "prepare-hmm-knn-research-data",
        "replay-eval",
        "replay-hmm-knn",
        "research",
        "research-hmm-knn",
        "run-discovery",
        "run-hmm-knn-experiments",
        "run-historical-research-cycle",
        "run-research-experiment",
        "train-model",
        "write-hmm-knn-sweep-datasets",
    }
)


def normalize_command_name(command: str | None) -> str:
    return str(command or "").strip().lower()


def is_research_command(command: str | None) -> bool:
    return normalize_command_name(command) in RESEARCH_COMMANDS
