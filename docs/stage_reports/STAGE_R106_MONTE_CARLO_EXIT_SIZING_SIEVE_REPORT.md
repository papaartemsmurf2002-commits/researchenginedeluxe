# Stage R106 Monte Carlo Exit And Sizing Sieve Report

Date: 2026-06-09

Work packet: `docs/work_packets/WPR106-80-monte-carlo-exit-sizing-sieve.md`

## Scope

WPR106-80 reran the latest strategy evidence through an offline Monte Carlo,
fixed-barrier, and Martingale sizing sieve. It used the user-requested cost
assumption:

- taker commission: 0.0432% per side;
- round-trip commission: 0.0864%;
- funding ignored;
- slippage ignored for this specific offline analysis.

The packet stayed research-only and did not create candidate packs, live/paper
artifacts, orders, runtime changes, live config writes, or actual sizing logic.

## External Research Check

Primary or research sources used:

- Vezeris, Kyrgos, and Schinas (2018), "Take Profit and Stop Loss Trading
  Strategies Comparison in Combination with an MACD Trading System":
  https://www.mdpi.com/1911-8074/11/3/56
- A 2025 Financial Innovation crypto study using information-driven bars,
  triple-barrier labeling, and deep learning:
  https://link.springer.com/article/10.1186/s40854-025-00866-w
- Leung and Zhang, "Optimal Trading with a Trailing Stop":
  https://ideas.repec.org/p/arx/papers/1701.03960.html
- Moallemi and Wang, "A Reinforcement Learning Approach to Optimal Execution":
  https://moallemi.com/ciamac/papers/rl-exec-2021.pdf

Interpretation for this branch:

- fixed TP/SL and triple-barrier exits are valid research candidates, but they
  need path-order evidence and sensitivity testing;
- trailing/optimal-stopping exits are path-dependent and should not be judged
  from aggregate fixed-hold returns alone;
- RL/optimal-stopping exits remain a later model family requiring execution
  timing data, not a quick optimizer tweak;
- every exit family must beat transparent baselines after costs.

## Artifacts

Generated outputs:

- `data/research/monte_carlo_exit_sizing/wpr106_80/wpr106_80_monte_carlo_exit_sizing_summary.json`
- `data/research/monte_carlo_exit_sizing/wpr106_80/wpr106_80_strategy_monte_carlo.csv`
- `data/research/monte_carlo_exit_sizing/wpr106_80/wpr106_80_fixed_barrier_audit.csv`
- `data/research/monte_carlo_exit_sizing/wpr106_80/wpr106_80_monte_carlo_exit_sizing_report.md`

The analyzer evaluated 34 strategy rows and 24 fixed-barrier audits with
10,000 Monte Carlo bootstrap paths.

## Results

The WPR106-79 archive-backed KNN rows were rejected as expensive-optimizer
candidates before trade-level Monte Carlo. The 2024 larger-validation matrix
showed negative after-cost expectancy for all tested BTC/ETH KNN and meta rows.

The only offline-positive rows were side decompositions of the WPR106-74 BTC
sparse rows:

- BTC aggTrade-contrarian sparse volatility breakout, long-only fixed hold:
  265 trades, mean return +0.008405, win rate 0.524528, observed compound
  return +5.785230, observed max loss streak 6, Monte Carlo 5th percentile
  terminal return +0.861093, and terminal-negative probability 0.0072.
- BTC price-only sparse volatility breakout, long-only fixed hold:
  258 trades, mean return +0.007293, win rate 0.550388, observed compound
  return +3.824832, observed max loss streak 5, Monte Carlo 5th percentile
  terminal return +0.382658, and terminal-negative probability 0.0198.

These rows are not candidate-ready because long-only was only an offline
side decomposition. The current `sparse_event_filter_v1` cannot express a true
long-only or side-veto contract, and no split/cost/stability gate has evaluated
that exact event population.

All conservative 1:2 fixed TP/SL variants were negative in the offline MAE/MFE
audit. Ambiguous paths were treated as stop-first because MAE/MFE does not prove
which barrier hit first. Nineteen fixed-barrier audits had more than 25%
ambiguous paths, so lower-timeframe triple-barrier reruns are required before
using fixed TP/SL conclusions.

Martingale x1.5 is blocked. With a 0.0864% round-trip fee, a 1:2 payoff and
1.5x size progression is not a true recovery system after moderate loss
streaks. Fee-positive recovery lasts only:

- 2 prior losses for a 0.3% stop;
- 3 prior losses for a 0.5% stop;
- 5 prior losses for a 1.0% stop;
- 6 prior losses for 1.5% and 2.0% stops.

The Monte Carlo p95 loss streaks on fixed TP/SL variants were far above those
thresholds, and simulated Martingale ruin probability was positive for every
fixed TP/SL row. No Martingale row was allowed for follow-up.

## Decision

Do not run expensive optimizer sweeps on KNN, fixed TP/SL, or Martingale rows
from the current evidence.

The next goal should be a focused BTC sparse side-veto packet:

- add a true research-only `allowed_sides` or side-veto parameter to
  `sparse_event_filter_v1`;
- rerun the two BTC long-only sparse theories as actual strategy candidates;
- include no-trade, transparent, and short-veto controls;
- if the true long-only rows survive split and cost-stress evidence, then open
  a larger optimizer packet around sparse long-only selection and
  sequence-proven lower-timeframe exits.

## Validation

Passed:

```powershell
python -m compileall -q src/tradingbotsuite/research/monte_carlo_exit_sizing.py
$env:PYTHONPATH='src'; python -m pytest tests/tradingbotsuite/test_monte_carlo_exit_sizing.py -q
```

The analyzer run completed:

```powershell
$env:PYTHONPATH='src'; python -m tradingbotsuite.research.monte_carlo_exit_sizing --output-dir data/research/monte_carlo_exit_sizing/wpr106_80 --paths 10000 --seed 10680 --taker-fee-rate 0.000432
```
