from __future__ import annotations

from tradingbotsuite.optimization.candidate import CandidateResult


def composite_score(result: CandidateResult) -> float:
    return result.final_score
