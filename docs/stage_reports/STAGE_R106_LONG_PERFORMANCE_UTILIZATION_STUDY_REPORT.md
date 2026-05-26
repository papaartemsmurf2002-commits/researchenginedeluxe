# Stage R106 Long Performance Utilization Study Report

Date: 2026-05-26
Work packet: `docs/work_packets/WPR106-19-long-performance-utilization-study.md`

## Scope

Second performance and utilization pass for the R106 research workflow. This was
measurement-first: no runtime source code was changed. The run used existing
benchmark surfaces plus an isolated bounded BTC candidate-depth exact-discovery
probe under the WPR106-19 artifact root.

All artifacts remain research-only, observe-only, and `promotion_ready: false`.
No live fetch, live runtime-mode change, live configuration write, order
placement, candidate-pack write, or candidate-ready performance claim was made.

## UI Command

PowerShell one-line operator UI command:

```powershell
$env:TBS_OPERATOR_UI_ENABLED='true'; $env:TBS_OPERATOR_UI_SECRET='operator-secret'; $env:TBS_BINANCE_MARKET_STREAMS_ENABLED='false'; tradingbotsuite serve --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/ui/research` and use `operator-secret` unless the
operator overrides the secret.

## Measurement Artifacts

Primary summary:

- `data/research/operator_runs/performance_utilization_wpr106_19/measurement_summary.json`

Runs:

- Hardware saturation, 8 workers:
  `data/research/operator_runs/performance_utilization_wpr106_19/hardware_cpu8_gpu45/`
- Hardware saturation, 16 workers:
  `data/research/operator_runs/performance_utilization_wpr106_19/hardware_cpu16_gpu45/`
- Historical-cycle provider latest-month benchmark:
  `data/research/operator_runs/performance_utilization_wpr106_19/historical_provider_latest_month_repeat2/`
- Discovery run-manager deep benchmark:
  `data/research/operator_runs/performance_utilization_wpr106_19/discovery_deep_repeat5/`
- Isolated BTC candidate-depth exact-discovery probe:
  `data/research/operator_runs/performance_utilization_wpr106_19/exact_btc_probe_16/`

Machine observed: AMD Ryzen 7 7700, 8 physical cores, 16 logical CPUs. GPU
probe succeeded through CuPy and `nvidia-smi` telemetry.

## Results

Hardware saturation:

- 8 CPU workers saturated worker capacity at `99.06%`, but used only `49.53%`
  of logical CPU capacity.
- 16 CPU workers saturated logical CPU capacity at `87.88%` and increased the
  CPU probe from about `34.95M` to `53.07M` operations per second.
- The GPU 2048 matrix probe succeeded in both passes at about `26.5T` to
  `26.6T` approximate GFLOPS, with sampled GPU utilization peaking at `93%`.

Historical provider latest-month benchmark:

- Two repeats passed the benchmark gate.
- Mean cycle runtime was `24.73s`, with `25` candidate backtests per repeat,
  `60.74` candidate backtests per minute, and `2441.29` processed rows per
  second.
- Feature-cache reuse was measurable: cold feature build `2.795s`, warm reuse
  `1.518s`, a local timing ratio of `1.84x`.
- The synthetic optimizer parallel benchmark showed `3.60x` speedup at
  4 workers with equivalent hashes.
- Artifact overhead was material even in this small provider benchmark:
  `39.26MB` across `1737` files, including backend comparison artifacts.
- Backend comparison showed that vector/CUDA are not automatically faster for
  this artifact-producing provider benchmark shape: median runtime sums were
  reference `2054ms`, CUDA `2114ms`, vector `22384ms`, and reference CPU48
  `25056ms`.

Discovery run-manager benchmark:

- Deep repeat-5 benchmark passed the gate.
- Mean full-run elapsed time was `0.646s`, resumed elapsed time was `0.462s`,
  and artifact overhead was about `16.9KB` per completed trial.
- This benchmark is a run-manager/resume/snapshot guardrail, not a replacement
  for exact candidate-depth KNN timing.

BTC candidate-depth exact-discovery probe:

- Probe used the active catalog BTC candidate-depth fixture
  `btcusdt-public-archive-candidate-depth-v1` with `221952` primary rows.
- 16 exact-discovery trials took `1033.65s`.
- Stage timing: real context preparation `105.95s`; trial execution `927.50s`.
- Artifact write share during the bounded compute probe was only `0.035%`, so
  this was calculation-dominated rather than write-dominated.
- Cache hit rates were high for GMM and label/split reuse (`0.875` each), and
  neighbor cache hit rate was reported as `0.6875`.
- External utilization sampling saw low-to-moderate Python CPU use, about
  `13.65%` of 16-logical CPU capacity, and low GPU use, about `2.4%` average.
  The runner's parent-process CPU telemetry intentionally undercounts process
  pool children, so the external sample is the more useful directional signal.
- Peak sampled Python working set was about `10.0GB`.

Completed BTC exact final manifest evidence:

- The completed BTC exact-discovery manifest records `570240/570240` trials.
- A final rebuild/finalization pass wrote or accounted for `570555` files and
  about `7.08GB`, with `86.37%` artifact-write wall-time share and `78.19s`
  in resume-state merge.
- That explains the observed low-utilization periods after compute-heavy work:
  final ledger/manifest reconstruction and broad artifact accounting are
  I/O-bound and intentionally durable.

## Interpretation

The system can saturate this machine when the task is pure CPU process work:
the 16-worker saturation probe used most logical CPU capacity. The large
calculation path does not behave like the synthetic saturation probe. Exact
candidate-depth discovery is dominated by KNN/materialization work with high
memory pressure, process-pool child accounting gaps, and cache-group shape. GPU
is mostly idle in that workflow because current exact KNN/search work is CPU
and host-memory bound.

Historical-cycle latest-month provider work is fast at this scale. The larger
costs there are artifact-producing backtests, backend comparison, split/cost
validation, and file volume. Feature caching already helps and should be
preserved aggressively.

There are two distinct low-utilization classes:

- Calculation phases that do not fully exploit all cores because of KNN/cache
  grouping, memory bandwidth, child-process shape, or Python/scikit-learn
  execution.
- Durability phases that are supposed to be lower CPU: state recovery, ledger
  rebuilds, Parquet/JSON artifact writes, hashing, and artifact indexing.

## Safe Speedup Recommendations

1. Do not globally raise exact-discovery workers from 8 to 16 just because the
   hardware probe can saturate 16 logical CPUs. The exact candidate-depth probe
   showed low average CPU capacity use but high memory footprint; previous
   48-worker Windows runs were unstable. Test 8, 12, and 16 workers with the
   same bounded candidate-depth probe before changing the default.
2. Keep cache-affinity ordering and full cache-group chunks for unbounded exact
   discovery. The largest speed lever remains computing expensive KNN bases
   once and evaluating threshold variants from cached arrays.
3. Add finer exact-discovery timing before algorithm changes: context prep,
   feature materialization, KNN base miss, KNN threshold hit, child-process
   startup, process tail wait, artifact write, and final ledger rebuild. Parent
   process CPU telemetry is not enough.
4. Reduce finalization I/O carefully. The completed BTC final pass shows
   `570555` files and `7.08GB` of artifact accounting with `86.37%` write share.
   A safe improvement would stream/chunk final ledger rebuilds and avoid broad
   artifact rescans when immutable trial JSON and state hashes prove no compute
   changed. Do not weaken per-trial durability or atomic state writes.
5. Preserve and broaden feature-cache reuse for repeated BTC/ETH, modern-window,
   and analysis paths. The provider benchmark measured a clean cold-to-warm
   feature improvement.
6. Parallelize shortlisted split/cost-stress validation only after adding
   manifest-order preserving execution and focused tests. The synthetic
   optimizer benchmark shows independent work can scale, but artifact-producing
   backtests have different overhead.
7. Treat CUDA as targeted diagnostic/accelerated screening only. Current
   provider and exact-discovery measurements do not justify moving broad KNN or
   artifact-producing backtests to GPU without a device-resident many-candidate
   design and parity evidence.

## Validation

- `python -m compileall -q src\tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests\contracts -q`
  - `427 passed`

## Residual Risk

This study identifies where to speed up safely, but it does not change the
runtime defaults. A future optimization packet should add child-process timing
telemetry first, then run controlled worker-count probes on BTC and ETH
candidate-depth data before raising concurrency or changing calculation paths.
