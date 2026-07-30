# Full FEMM Pipeline Run — Summary

*Run date: 2026-07-31. All solves executed headlessly through pyFEMM at the
physical coil depth. Sanity suite: **28 passed / 0 failed / 0 skipped** (see
`sanity_check_report.md`).*

## Depth correction (this run's headline change)

The 2D planar model historically solved with **Depth = 1 mm**, making every
absolute flux/M/voltage 25× too small. The real coil axial length is now a
config parameter (`COIL_DEPTH_MM = 25` — an assumption matching the
sanity-check reference coil; **set it to your physical coil length if it
differs**) and is passed to every solver call plus the base-file header.
Verification: M at 20 kHz went from 0.037078 → 0.926949 µH — exactly ×25,
confirming pure linear depth scaling. All ratios (N², dip %, DOE trends) are
unchanged, as theory requires.

## Results at physical depth

| Quantity | Value |
|---|---|
| Baseline M (100/100 turns, 20 kHz) | **0.9270 µH** (`config.M0_UH`) |
| DC (magnetostatic) M | 0.1497 µH |
| RX open-circuit voltage at 2.5 A | 0.291 V |
| Detection dip with wheel present | **91.7 %** (M 0.927 → 0.077 µH) |
| M drift across 10–20 kHz | 1.5 % |
| DOE optimum (feasible) | dx = −4 mm, θ = −10° → **M = 1.322 µH (+43 %)** |
| Largest feasible coil scale at optimum | 1.0× (1.1–1.5× collide with the rail) |

## Standing findings (from the earlier bug-fix pass, still true)

1. **FEMM clears the selection after every move/rotate/scale operation** — the
   group must be re-selected before each op. This silent no-op invalidated all
   pre-2026 DOE tilt results and the old 1.5× scale.
2. The whole dx = −8 mm column and the (−4 mm, −15°) corner are physically
   infeasible (coil-rail collision); they are excluded from the RSM fit and
   recorded in `doe_rsm_result.json`.
3. The M ∝ N² turn-scaling law is FEMM-verified (≤1.8 % deviation, 50–200
   turns); the linear-in-area scaling used by the analytic extrapolations is
   NOT FEMM-verified — treat large-area design points as guidance only. At
   the 200-turn / 0.2 m² design point the analytic M is ~10 mH with k ≈ 0.15,
   plausible but unvalidated.

## Solver validation

* Known-coil self-check: 212 turns (70 % packing, 30/40 mm × 25 mm window)
  solved axisymmetric in FEMM: **L = 3.180 mH vs Wheeler's formula 3.267 mH
  (2.7 % apart)**.
* Faraday's law V = ωΦ holds on every AC solve in every CSV (≤1 %).
* M independent of drive current to <0.005 %.
* Free-space dipole bound (8.39 µH at the model's 121 mm separation) upper-
  bounds the rail-shielded FEMM M0 (0.93 µH), as it must.

## Files
- Fresh: `coil_parameter_sweep_femm.csv`, `frequency_sweep_femm.csv`,
  `wheel_dip.json`, `wheel_dip_result.txt`, `femm_live_result.txt`,
  `doe_rsm_result.json`, `scaled_geom_result.json`,
  `femm/optimal_geom_scaled.fem(.ans)`, `coil_parameter_sweep.csv`,
  `optimal_design.json`, all 13 figures, refreshed notebooks,
  `sanity_check_report.md`.
- Base model `femm/InternMadebyPratham.FEM`: geometry untouched; only the
  `[Depth]` header updated 1 → 25 mm to match the solver setting.
