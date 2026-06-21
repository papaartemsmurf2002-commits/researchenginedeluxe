from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_worker_job_store_direct_import_is_fresh_interpreter_safe() -> None:
    result = _run_python(
        "from tradingbotsuite.v2.workers.job_store import WorkerJobStore; "
        "print(WorkerJobStore.__name__)"
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "WorkerJobStore"


def test_data_quality_package_lazy_job_export_remains_compatible() -> None:
    result = _run_python(
        "from tradingbotsuite.v2.data_quality import run_data_quality_job; "
        "print(callable(run_data_quality_job))"
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "True"


def _run_python(command: str) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "src")
    return subprocess.run(
        [sys.executable, "-c", command],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
