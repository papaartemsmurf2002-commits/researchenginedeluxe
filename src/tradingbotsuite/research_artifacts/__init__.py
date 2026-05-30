"""Research artifact gates. Read docs/REPO_STRUCTURE_AND_DEPENDENCY_FUSE.md before candidate-pack edits."""

from __future__ import annotations

from tradingbotsuite.research_artifacts.candidate_pack import (
    RESEARCH_CANDIDATE_PACK_VERSION,
    ResearchCandidateGate,
    ResearchCandidateGateContext,
    ResearchCandidatePackResult,
    build_research_candidate_gate_context,
    evaluate_research_candidate_gate,
    evaluate_research_candidate_gate_from_context,
    evaluate_research_candidate_gate_from_row,
    source_capability_gate_reasons,
    validate_research_candidate_pack_manifest,
    write_research_candidate_pack,
)

__all__ = [
    "RESEARCH_CANDIDATE_PACK_VERSION",
    "ResearchCandidateGate",
    "ResearchCandidateGateContext",
    "ResearchCandidatePackResult",
    "build_research_candidate_gate_context",
    "evaluate_research_candidate_gate",
    "evaluate_research_candidate_gate_from_context",
    "evaluate_research_candidate_gate_from_row",
    "source_capability_gate_reasons",
    "validate_research_candidate_pack_manifest",
    "write_research_candidate_pack",
]
