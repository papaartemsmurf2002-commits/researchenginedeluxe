# WPR106-145 Direct KNN Veto Lead Controls

Date: 2026-06-12
Owner: Codex Research Agent
Status: closed

## Objective

Stress-test the two WPR106-137 KNN-veto ensemble rows surfaced by WPR106-144
before treating them as more than narrow research-only leads:

- `vetoensemble-0984617d185c319b`;
- `vetoensemble-2b025e21f7235d09`.

The packet keeps the 2024-01-01 through 2026-04-30 pre-May window as the only
selection and control-design window. May 2026 remains benchmark-only after each
fixed control definition. The goal is to determine whether the leads survive
member ablation, cross-symbol/WPR133 dependence checks, no-KNN source-trade
baselines, and simple cluster/month sensitivity.

## Allowed Paths

- `docs/work_packets/WPR106-145-direct-knn-veto-lead-controls.md`
- `docs/stage_reports/STAGE_R106_DIRECT_KNN_VETO_LEAD_CONTROLS_REPORT.md`
- `docs/ORCHESTRATOR_STAGE_LEDGER.md`
- `docs/KNOWN_ISSUES.md`
- `data/research/wpr106_145_direct_knn_veto_lead_controls/**`

## Inputs

- `data/research/wpr106_137_diversity_constrained_knn_veto_ensemble/**`
- `data/research/wpr106_136_cross_family_knn_trade_veto_search/**`
- `data/research/wpr106_144_direct_source_family_stability_benchmark/**`

## Boundaries

- Research-only, observe-only, promotion-ready false.
- No candidate pack, paper/live artifact, order placement, sizing change,
  runtime-mode change, live configuration write, or promotion claim.
- Control definitions and selected leads must come from pre-May and WPR106-144
  evidence only.
- May 2026 may be replayed only after each control definition is fixed.
- No-KNN controls are diagnostic baselines, not valid strategy claims.
- Replays must preserve embedded source costs, equal sleeves, same-symbol
  overlap skipping, and explicit accepted-trade daily caps.
- CUDA is not expected. CPU/vectorized pandas/accounting is sufficient and no
  speedup claim is allowed unless a real CUDA path is used and verified.
- If a blocking correctness risk is found, update `docs/KNOWN_ISSUES.md`.

## Evidence Plan

1. Load the WPR106-137 selected lead rows and their raw overlay member trade
   stores.
2. Recompute the WPR106-144 lead variants from raw WPR106-137 overlay trades
   using daily caps 1, 3, and 5 where relevant.
3. Run member ablations: drop each overlay member and isolate each overlay
   member.
4. Run dependency controls: remove WPR106-133 lead-lag members, remove
   `cross_symbol_relative_strength` members, and remove all ETHUSDT-only or
   BTCUSDT-including subsets where applicable.
5. Run no-KNN diagnostic baselines by combining the underlying source trades
   before KNN veto filtering.
6. Run cluster/month sensitivity by removing the best pre-May month, worst
   pre-May month, and most active pre-May month before checking whether the
   profile remains plausible.
7. Replay every fixed non-diagnostic and diagnostic control on May 2026 as a
   benchmark only.

## Validation

Run focused script compile, then the branch baseline:

```powershell
python -m compileall -q data/research/wpr106_145_direct_knn_veto_lead_controls/scripts
python -m compileall -q src/tradingbotsuite
$env:PYTHONPATH='src'; python -m pytest tests/contracts -q
```

Completed:

- `python -m compileall -q data/research/wpr106_145_direct_knn_veto_lead_controls/scripts`
- `python -m compileall -q src/tradingbotsuite`
- `$env:PYTHONPATH='src'; python -m pytest tests/contracts -q` -> 460 passed.

## Closeout

WPR106-145 keeps the WPR106-144 KNN-veto ensemble leads research-only and
fail-closed. All six baseline daily-cap variants were pre-May profile-ok and
May-positive, and 26 of 39 non-diagnostic controls survived. However, the
positive May behavior is materially concentrated in the same WPR106-133
`cross_symbol_relative_strength` overlay member. Isolating that member
produced +0.059766 May, while the other isolated members were May-negative.
Removing WPR106-133/cross-symbol-relative-strength made `veto2b025` negative
in May at all caps, and removing WPR106-133 from `veto098` also made May
negative.

The no-KNN diagnostic baselines were mixed: `veto098` no-KNN was May-positive
but failed pre-May profile checks with 9 losing months, while `veto2b025`
no-KNN cap 3/5 had a plausible pre-May profile but failed May. The next useful
work is a direct causal audit of the WPR106-133 relative-strength overlay
member itself, not a candidate-pack attempt for these ensembles. No candidate
pack, paper/live artifact, order/sizing/runtime change, live configuration
write, CUDA speedup claim, or promotion claim was created.
