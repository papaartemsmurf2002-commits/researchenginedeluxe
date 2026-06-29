# V2-AUDIT-ID: V2-AUD-COLLECT-001
# V2-CONTRACTS: docs/contracts/collector_job_contract.md
# V2-BOUNDARY: research_only, durable_collectors, no_live_imports
# V2-OWNER: v2_collectors
"""V2 collector bounded context."""

from __future__ import annotations

from tradingbotsuite.v2.collectors.jobs import (
    CollectorJobRecord,
    CollectorJobStatus,
    run_collector_job,
)
from tradingbotsuite.v2.collectors.templates import (
    ResearchCollectorAdapterTemplate,
    collector_template_from_gap_request,
)

__all__ = [
    "CollectorJobRecord",
    "CollectorJobStatus",
    "ResearchCollectorAdapterTemplate",
    "collector_template_from_gap_request",
    "run_collector_job",
]
