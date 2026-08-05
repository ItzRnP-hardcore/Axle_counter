# Sanity Check Report

Reference coil: ri=30 mm, ro=40 mm, l=25 mm, packing=0.7, wire d=1.024 mm, f=20 kHz, Ip=2.5 A

**Result: 28 passed / 0 failed / 0 skipped**


## reference coil

- ℹ️ **geometry** — ri=30 mm, ro=40 mm, l=25 mm, pf=0.7, wire d=1.024 mm -> N = 212 turns
- ℹ️ **inductance** — Wheeler L = 3.267 mH, loop-formula L = 8.548 mH (ratio 2.62; loop formula assumes a thin bundle, so a factor of ~1.5-2x spread at this aspect ratio is expected)
- ✅ **repo loop formula within 3x of Wheeler** — if this failed, one of the two L models would be misapplied
- ℹ️ **electrical** — wire 46.7 m, Rdc=0.953 ohm, Rac=1.325 ohm (skin depth 0.461 mm), Q=310, C_res=19.38 nF, V_cap=1026 V pk at Ip=2.5 A
- ✅ **skin depth < wire radius at operating frequency** — delta=0.461 mm vs a=0.512 mm -- AC resistance correction matters
- ℹ️ **free-space M estimate (100/100 turns)** — coplanar dipole M = 8.39 uH at d = 120.8 mm (overestimates somewhat at d/r = 3.5)
- ✅ **model depth matches config.COIL_DEPTH_MM** — .FEM header 25 mm vs config 25 mm -- these must agree or absolute FEMM numbers are mis-scaled
- ℹ️ **depth scaling** — 2D planar model solved at Depth = 25 mm (the real coil axial length), so FEMM fluxes/M/voltages are absolute physical values. M0 = 0.927 uH vs 8.39 uH free-space dipole bound; FEMM sitting below free space is expected -- the steel rail between the coils shields flux at AC.
- ✅ **FEMM M0 does not exceed free-space upper bound** — free space (no rail) must upper-bound the shielded rail geometry
- ✅ **config A_REF matches pi*r^2**

## FEMM self-check (known coil)

- ℹ️ **measured** — FEMM (axisymmetric, N=212) L = 3.180 mH vs Wheeler 3.267 mH (2.7% apart) vs loop formula 8.548 mH
- ✅ **FEMM matches Wheeler's formula (10%)** — units, circuit-turns handling and solver setup are trustworthy

## coil_parameter_sweep_femm.csv

- ✅ **open-circuit induction V_rx = w*flux (every row, 1%)** — 8/8 rows obey Faraday's law
- ✅ **TX current equals requested drive**
- ✅ **M follows N^2 turn scaling (12%)** — ratios vs (N/100)^2: N=50: 0.9%, N=100: 0.0%, N=150: 0.9%, N=200: 1.8%
- ✅ **config.M0_UH matches the 100-turn FEMM row (1%)** — config 0.92695 vs CSV 0.92695 uH
- ✅ **M independent of drive current (linearity, 0.5%)** — max spread 0.000%

## frequency_sweep_femm.csv

- ✅ **V_rx = w*flux at every frequency (1%)** — 21/21 rows pass
- ✅ **M varies smoothly with frequency (<25% over 10-20 kHz)** — spread 1.5% (eddy currents in the rail cause a mild drift; a jump would mean a broken solve)
- ✅ **L_TX positive and finite**

## coil_parameter_sweep.csv

- ✅ **M reproduces from config anchor (0.1%)** — max err 0.0000%
- ✅ **Vs_pp = 2*w*M*Ip (0.1%)**
- ✅ **area column = A_REF * scale**

## optimal_design.json

- ✅ **every row obeys L/M/C/Vcap/Vrx identities (1%)** — 4/4 rows pass
- ✅ **recommended row: cap voltage within its rating** — V_cap = 992 V vs 1000 V class
- ✅ **recommended Q*Vrx_oc = Vrx_tuned (1%)**

## wheel_dip.json

- ✅ **dip arithmetic (M0-M1)/M0** — stored 91.73% vs recomputed 91.73%
- ✅ **wheel reduces coupling (M1 < M0)** — 0.9269 -> 0.0767 uH
- ✅ **voltage ratio tracks M ratio (2%)** — for a fixed-current TX drive, V_rx must scale with M

## doe_rsm_result.json

- ✅ **optimum lies inside the sampled DOE grid** — x=-4.00, y=0.00, theta=-10.00
- ✅ **verified optimum >= 95% of best sampled run** — optimum 1.3217 vs best sampled 1.3217 uH

## axle_counter_sweep_data.csv

- ✅ **V_cap = I/(w*C) at resonance (1%)**
- ✅ **uncompensated V >= resonant V on every row**

## femm_live_result.txt

- ✅ **AC section obeys V = w*flux (1%)** — 0.291210 V vs w*flux = 0.291213 V
