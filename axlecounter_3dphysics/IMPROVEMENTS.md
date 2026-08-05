# Axle Counter 3D Physics — Current State & Change Record

Two sections: **Part 1** is the durable reference (how the project is wired and
the rules you must not break). **Part 2** is the record of the most recent
change pass. Earlier session-by-session narrative has been removed — the
codebase, not this file, is the source of truth for how things work today.

---

# Part 1 — Reference

## How to run it

```bash
py -3 run_all.py            # everything, in dependency order
py -3 run_all.py --list     # show the plan without running
py -3 run_all.py --skip-femm    # analytics + figures only (no solver)
```

`run_all.py` (project root) is the single entry point. `run_all.bat` is a
double-clickable wrapper. The three batch files in `simulation_and_femm/`
(`run_femm.bat`, `run_sweep.bat`, `run_wheel.bat`) each run one solver script.

## Layout

| Folder | Contents |
|---|---|
| `config.py` (root) | every hardware parameter, path and identifier |
| `simulation_and_femm/` | live FEMM solves + the shared `femm_utils` helper |
| `optimization_and_design/` | DOE/RSM optimiser, geometry apply, design tables |
| `analysis_and_reporting/` | analytic sweeps, figures, notebooks, sanity suite |
| `reports/` | every generated CSV/JSON/PNG + `sanity_check_report.md` |
| `old_files/` | deprecated scripts and pre-refactor backups |

## Ground truth — TX/RX mapping

Read directly from the `[NumBlockLabels]` block of
`femm/InternMadebyPratham.FEM`:

| Coil | Side | Label x (mm) | FEMM group | Circuit |
|---|---|---|---|---|
| **TX** (energised, 2.5 A) | **RIGHT** (+x) | +47.02, +116.75 | 2 | `"New Circuit"` |
| **RX** (open / sense) | **LEFT** (−x) | −47.44, −116.91 | 1 | `"Receiver"` |

Each coil is drawn as **two** bundles (the go and return conductors), 70 mm
apart, which is why two x-coordinates are listed per coil.

`config.py`, `femm_sweep.py`, `make_figs.py` and `generate_wheel_figure.py` all
agree with this table.

## Rules that must not be broken

1. **FEMM auto-saves the open document when it analyzes.** Any script that
   calls `mi_analyze()` on the base `.FEM` silently mutates it. Always work on
   a scratch copy (`femm_utils.open_scratch()`).
2. **FEMM clears the selection after every move/rotate/scale.** The group must
   be re-selected before *each* operation or it silently does nothing.
3. **Solve time-harmonic, not magnetostatic.** The base file is stored at
   `[Frequency] = 0`; every solver script sets `config.FREQUENCY_HZ` before
   analysing. A DC solve reports zero induced RX voltage and understates
   coupling ~6×.
4. **Depth must match.** The 2D planar model computes flux *per unit depth*, so
   `config.COIL_DEPTH_MM` scales every absolute flux/M/voltage and must
   equal the `[Depth]` header in the `.FEM`. `sanity_check.py` enforces this.
5. **Paths come from `config`**, never from a script's own `__file__` — the
   scripts live in subfolders, so `dirname(__file__)` is one level too deep.
6. **A `.fem`/`.ans` pair is only valid if the `.ans` is at least as new as the
   `.fem`.** Otherwise the solution belongs to a different geometry.
7. **`M ∝ N²` is FEMM-verified; the linear-in-area term is NOT.** The area
   scaling used by the analytic extrapolations is unvalidated — treat large
   area scale factors as order-of-magnitude guidance only.
8. **Nothing writes back to `config.py`.** Results go to `reports/`, so a
   config value is always an input and can never become a stale cached output.

## Current verified results

| Quantity | Value |
|---|---|
| Baseline M (212/212 turns, 20 kHz) | **21.4651 µH** (`config.M0_UH`) |
| Magnetostatic M (f = 0) | 5.2995 µH |
| RX open-circuit voltage at 2.5 A | 6.7435 V |
| Detection dip with wheel present | **87.99 %** (M 21.4651 → 2.5785 µH) |
| M drift across the swept band | 0.2 % |
| DOE optimum (feasible) | dx = -4 mm, θ = -15° → **M = 31.9653 µH** |
| Largest feasible coil scale at optimum | 1.0× |
| Air-core recommendation | 1000 V cap class: 91 turns, 18 AWG, 20 kHz, 40.39 nF → 248.5 V tuned RX |

Solver validation: a known reference coil (212 turns, 30/40 mm × 25 mm window)
solved axisymmetric in FEMM gives **L = 3.180 mH vs Wheeler's formula 3.241 mH
(1.9 % apart)**. Sanity suite: **28 passed / 0 failed / 0 skipped**.

---

# Part 2 — Change record (2026-08-05)

## Comment cleanup

Every script's comments were rewritten. Historical narrative ("the old version
did X", "why the rewrite", "fixed over the original") was deleted; the
*invariants* those comments protected were kept and restated as present-tense
rules (the list in Part 1). Explanatory comments describing what the code
actually does were added throughout. Six dead constants
(`OPTIMAL_M_uH`, `OPTIMAL_X`, `OPTIMAL_Y`, `OPTIMAL_THETA`, `SCALED_M_uH`,
`SCALED_FACTOR`) were removed from `config.py` — nothing read them and they
held pre-depth-fix values that contradicted the live anchor.

## New: `run_all.py`

There was no orchestrator; each batch file ran a single script. `run_all.py`
now runs all 14 pipeline stages in dependency order (live solves → analytics →
notebooks → figures → sanity gate), sequentially because FEMM is
single-instance, with timing, a pass/fail summary and a non-zero exit code on
failure.

## Path breakage fixed (from the subfolder reorganisation)

Four files derived the project root from their own location, which after the
move pointed one level too deep:

| File | Symptom |
|---|---|
| `simulation_and_femm/femm_run_once.py` | looked for the model at `simulation_and_femm/femm/…` — **did not exist, the run failed** |
| `analysis_and_reporting/make_figs.py` | wrote to a stray `analysis_and_reporting/reports/figures/`; couldn't find the legacy CSV, so **figures 05–09 were silently skipped** and went stale |
| `analysis_and_reporting/generate_wheel_figure.py` | couldn't find `_wheel_work.*` → **figure 11 never regenerated** |
| both `.ipynb` notebooks | `import config` → `ModuleNotFoundError`, **dead on cell 1** |

All now resolve through `config`; the notebooks walk up until they find
`config.py`, so they work from either the notebook folder or the project root.

## Contradictions found and corrected

1. **TX/RX sides were documented backwards** in this file. The code was always
   right; only the prose was wrong. Corrected against the `.FEM` (Part 1 table).
2. **`doe_rsm_result.json` contradicted itself.** When the fitted optimum is
   infeasible, `axle.py` fell back to the best sampled point but left
   `diagnostics` describing the *rejected* fit — the file reported
   `optimum.theta = -10` alongside `diagnostics.theta.used = -15`. Diagnostics
   are now updated on fallback and record `rejected_fit_value`.
3. **`make_figs.py` could pair a geometry with a foreign solution.** `axle.py`
   re-saves `temp.fem` on every DOE point, so after an infeasible final solve
   the `.fem` held a geometry that was never solved while `temp.ans` came from
   a different point — figure 01 drew one configuration's coils over another's
   flux map. Pairs are now rejected unless the `.ans` is at least as new as the
   `.fem`, the preferred source is `_live_tmp.*` (freshly-solved base
   geometry), and figure 01 names its source in the title.
4. **`sweep_analysis.ipynb` markdown was refuted by its own CSV** — it claimed
   resonance leaves "tens or hundreds of volts instead of kilovolts", while the
   `Capacitor_Voltage_Peak_V` column it writes reaches 50 kV. Corrected to
   state that resonance *relocates* the kilovolts onto the capacitor. A scope
   note now marks that notebook's hard-coded `N_s = 60` / `A_p = 100 cm²` as a
   deliberate legacy model that does not match `config.py`.
5. **Single-source-of-truth leaks closed.** `femm_run_once.py` hardcoded the
   circuit names, frequency and model path; `calc_caps.py` hardcoded 20 kHz;
   `optimize_air_core.py` hardcoded `/100.0` instead of
   `config.BASELINE_TURNS`; `sanity_check.py` hardcoded `f=20kHz` in a regex,
   so changing the frequency would have made that check silently **SKIP**. The
   steel-wheel rectangle was duplicated between the solver and the figure
   script and now lives in `config.WHEEL_*`.
6. **Dangling references.** `run_femm.bat` was cited twice but never existed —
   it does now. `generate_notebook.py` / `generate_sweep_notebook.py` were
   cited but do not exist.
7. **Stale numbers** throughout this file refreshed; the air-core entry quoted
   the 2 kV table row while the script recommends the 1 kV row.

## Verification — physics unchanged

The full pipeline was re-run after the fixes (68 live FEMM solves, both
notebooks, all figures). Of 34 report files, **31 are byte-identical** to the
pre-fix run — every CSV, `wheel_dip.json`, `optimal_design.json`,
`femm_live_result.txt` and all 27 DOE runs. The only intended diffs are
`doe_rsm_result.json` (diagnostics now self-consistent), figure 01 (correct
source pair + labelled title) and `RUN_SUMMARY.md`. Sanity suite: **28 passed /
0 failed / 0 skipped**.

## Known gap — not fixed

`reports/figures/10_femm_doe_sweep.png`, `12_detection_dip.png` and
`13_design_table.png` are **produced by no script in the repo** (grep finds no
writer). They date from 2026-07-15 and do not refresh, so any claim that "all
13 figures" are fresh is true of only 10 of them. Either restore the script
that made them or treat those three as historical images.

## Canonical-coil rebuild (2026-08-05, session 5)

The project now describes **one** coil. Every physical parameter is defined
once in `config.py` and derived from five stated assumptions (ri = 30 mm,
ro = 40 mm, l = 25 mm, packing = 0.70, 18 AWG), from which the turn count
follows as N = 212 rather than being asserted.

### What changed in the model

| | Before | After |
|---|---|---|
| Turns per coil | 100 (unjustified) | **212** (derived from the winding window) |
| Coil bundle cross-section | 13.27 x 35.39 mm = 469.65 mm2 | **10 x 25 mm = 250 mm2** |
| Coil mean radius | 11.06 mm (matched nothing) | **35 mm** (= config.COIL_RADIUS_M) |
| Coil separation | 120.84 mm | **164.06 mm** |
| Material LamFill | 1 (100% solid copper) | **0.6984** (the true fill) |
| Wire, everywhere | 18 AWG / 16 AWG / 1.5 mm mixed | **18 AWG only** |
| Frequency, everywhere | 20 kHz / 25 kHz mixed | **20 kHz only** |
| M0 (measured) | 0.9269 uH | **21.4651 uH** |

The coils were translated outward because a true 35 mm-radius coil would
otherwise sit inside the rail head (which reaches x = 34.35 mm at coil height);
the original 6.60 mm inner clearance is preserved exactly. Backups of the
previous model are in `old_files/pre_212turn_backup/`.

### Results on the rebuilt model

- Detection dip **87.99 %** (M 21.4651 -> 2.5785 uH,
  RX 6.7435 -> 0.8101 V)
- M follows N^2 to within **0.5 %** across 50-400 turns (was 1.8 %) -- the
  consistent geometry and the corrected fill factor both improved it
- Sanity suite **28 passed / 0 failed / 0 skipped**

### Other corrections

1. **Wheeler's constant** was 31.6e-6; the exact imperial-to-SI conversion is
   0.8/0.0254 = 31.4961e-6. Corrected, so the code and the hand derivation now
   agree digit for digit (L = 3.241 mH vs FEMM 3.180 mH, 1.9 % apart).
2. **The "free-space upper bound" check was describing itself wrongly.** With
   the larger coils FEMM sits 1.42x ABOVE the point-dipole estimate, because
   that estimate treats each coil as a point 164 mm away while the facing
   conductor bundles are only ~94 mm apart. The check is now stated as a
   factor-of-3 band with the reasoning attached, instead of claiming a bound it
   never had.
3. **Notebooks now run in separate subprocesses.** Executing two in one process
   left the previous kernel's asyncio/zmq state behind on Windows and the second
   write failed with a spurious `OSError: [Errno 22]`.
4. **`RUN_SUMMARY.md` is now generated**, not hand-maintained -- it had drifted
   out of date every time the model changed.

### New deliverables

- `run_all.py` gained a final stage, `build_report.py`, which regenerates
  `reports/Axle_Counter_Full_Report.md` + `.pdf` and `reports/RUN_SUMMARY.md`
  entirely from live config/report data. Byline: **Prepared by Rudranarayan**.
- `analysis_and_reporting/md_to_pdf.py` renders Markdown (with LaTeX display
  math via matplotlib mathtext, since no LaTeX engine is installed) to PDF.
- `sanity_check.md` / `sanity_check.pdf` in the parent folder: a step-by-step
  hand derivation, theory stated before each calculation, checked against FEMM.
  `test.md` is superseded by it and now says so.
