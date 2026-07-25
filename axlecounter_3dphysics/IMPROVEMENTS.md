# Code Improvements — Efficiency & Hardware Integration

Applied 2026-07-15. Originals preserved in `_original_backup/`.

## What changed and why

### 1. Portable paths (removes machine-locked hard-coded directories)
Several scripts wrote results to a hard-coded Gemini scratch folder
(`C:\Users\rudra\.gemini\antigravity-ide\brain\...`). That path only exists on
one machine, so the pipeline broke on any other computer and silently scattered
outputs. All generators now write to **`config.OUTPUT_DIR` (= `./reports/`)**.

* `generate_data_points.py` → writes `reports/coil_parameter_sweep.csv`
* `femm_sweep.py` → writes `reports/coil_parameter_sweep_femm.csv`
* `generate_notebook.py`, `generate_sweep_notebook.py` → `reports/`
* `export_reports.py` → marked **DEPRECATED** (its job is now automatic)

### 2. Single source of truth for hardware parameters (`config.py`)
Frequency, drive current, circuit names, coil block-label coordinates and the
output directory are now defined **once** in `config.py`. Changing the operating
frequency or renaming a coil circuit no longer means hunting through five files.

New entries: `FREQUENCY_HZ`, `OUTPUT_DIR`, `TX_CIRCUIT`, `RX_CIRCUIT`,
`TX_LABELS`, `RX_LABELS`, `COIL_WIRE_BLOCK`.

### 3. Shared helper module (`femm_utils.py`)
The open → analyze → extract-mutual-inductance logic was copy-pasted across
`axle.py`, `femm_sweep.py` and `apply_best_geom.py`. It now lives in one place:

* `open_base(set_ac=True)` — open the FEM file and set the AC operating point
* `set_frequency(freq_hz)` — switch magnetostatic ⇄ time-harmonic
* `extract_mutual_inductance()` — returns `(M_uH, V_rx, flux_rx, I_tx)`

`femm` is imported lazily, so the module (and any tooling that imports it) loads
fine on machines without FEMM installed.

### 4. Correct physics: magnetostatic → time-harmonic (AC)  ⚠️ recommended
The base `.FEM` is saved with **`[Frequency] = 0` (magnetostatic)**. A real axle
counter is excited at 10–20 kHz. Magnetostatic solves ignore:
* **eddy currents induced in the steel rail** (the dominant loss + phase-shift
  mechanism), and
* **skin effect** in the copper.

Call `femm_utils.set_frequency(config.FREQUENCY_HZ)` before `mi_analyze()` to get
physically representative coupling and losses. This is wired into `open_base()`
but intentionally **not** force-written into your `.FEM` file — see the safety
note below.

## Safety note — your geometry file was NOT overwritten
`apply_best_geom.py` overwrites the base `.FEM` in place (and appends to
`config.py`). I left it untouched and did **not** run it, so your committed
geometry is exactly as you had it. Run it yourself when you're ready to bake in
the optimised geometry.

## Bug worth a look — FIXED (2026-07-25)
In `femm_sweep.py`, the coil labels were previously swapped (TX labels pointing to the `"Receiver"` circuit, and RX labels pointing to `"New Circuit"`). This has now been corrected so that the left coil (-x) correctly uses the `"New Circuit"` (TX) and the right coil (+x) uses the `"Receiver"` (RX) matching `config.py`.

## Live FEMM run — confirmation (2026-07-15)
`femm_run_once.py` was executed against your FEMM 4.2 install and solved the base
geometry at both frequencies. Fresh solver output:

| Quantity | Magnetostatic (f=0) | Time-harmonic (f=20 kHz) |
|---|---|---|
| RX induced voltage | 0.000 V | 0.01497 V (~15 mV) |
| Mutual inductance M | 0.00771 uH | 0.04764 uH |

This **confirms** the point in item 4: the magnetostatic model predicts *zero*
output voltage and understates coupling by ~6.2x. Your stored
`OPTIMAL_M_uH = 0.00771` is the magnetostatic value; the 20 kHz AC run supersedes
it. Re-run any time with `run_femm.bat`.

## Sweep rewrite + base-file repair (2026-07-15, session 2)
**Problem found:** the original `femm_sweep.py` (a) scaled coil *geometry* with
`mi_scale`, producing noisy non-monotonic "area" results, and (b) analysed the
**base .FEM in place** — and FEMM auto-saves on analyse, so the sweep overwrote
the base model (frequency set to 20 kHz, coil turns left asymmetric 100/-150).

**Fixes:**
- `femm_sweep.py` rewritten to (1) save a scratch working copy (`_sweep_work.fem`)
  before analysing, so the base is never touched again; (2) vary the coil only
  through block/circuit **properties** (turns + drive current) — no geometry.
- Base model `femm/InternMadebyPratham.FEM` **repaired**: frequency restored to 0
  (original magnetostatic), coil turns re-symmetrised to +100/-100 per coil,
  geometry (33 points / 32 segments / 6 labels) verified intact. The mutated
  version is preserved at `_original_backup/femm/InternMadebyPratham.FEM.mutated_*`.

**Clean DOE result (8 live solves @ 20 kHz):** M follows N^2 to within 3%
(M/N^2 ~= 3.7e-6 uH across N = 50..200); RX voltage scales linearly with turns
and drive current; M is independent of drive current — all physically correct.

Note: coil **area** is inherently geometric and cannot be a block property; study
it by redrawing the coil, not by rescaling against the fixed rail.

## Air-core redesign for wheel detection (2026-07-15, session 3)
Corrected the design premise: **no ferrite core** — the axle counter detects a
steel wheel by the DIP it causes in coil coupling, so the coils must stay
air-core and the goal is the strongest stable air-only coupling (best dip SNR).

- `optimize_air_core.py`: maximises RX signal / flux linkage subject to buildable
  ratings. Key identity V_rx/V_cap = M/L, so signal is limited by capacitor
  voltage rating -> a design table across 250/630/1000/2000 V cap classes.
  Recommended: 119 turns, 70 mm, AWG16, 25 kHz, 16 nF/2 kV -> ~4.1 V tuned RX.
- `femm_wheel_dip.py` + `run_wheel.bat`: LIVE FEM run that drops a steel wheel
  into the field. Result: mutual inductance falls 0.0371 -> 0.0031 uH = **91.7%
  detection dip** (RX 11.6 mV -> 1.0 mV). Confirms robust detection.
- Report rewritten around air-core wheel detection: detection principle, wheel
  flux map, dip quantification, optimal-design table, full component ratings
  (L, C_p, C_s, voltage/current ratings, Q, power), and a step-by-step coil
  construction guide. Ferrite recommendation removed.
