**Prepared by Rudranarayan**

Inductive axle counter: two air-core coils facing each other across a steel rail. A passing wheel disturbs their coupling, and that disturbance is the count. This report documents the finite-element model, the measured results and the resulting design.

Every figure in this report is generated from `config.py` and the live contents of `reports/`. It is rebuilt by `build_report.py` and therefore always describes the current state of the project.

---

## 1. Headline results

| Quantity | Value |
|---|---|
| Mutual inductance M0 (baseline) | 21.4651 µH |
| Turns per coil | 212 |
| Operating frequency | 20 kHz |
| TX drive current | 2.5 A peak |
| **Wheel detection dip** | **87.99 %** |
| M with / without wheel | 21.4651 → 2.5785 µH |
| RX voltage with / without wheel | 6.7435 → 0.8101 V |
| DOE optimum geometry | dx = -4 mm, θ = -15° → M = 31.9653 µH |
| Largest feasible coil scale | 1.0× |
| Sanity suite | 28 passed / 0 failed / 0 skipped |

> **The detection margin is large.** The wheel removes 88.0 % of the coupling, dropping the received signal from 6.74 V to 0.81 V — a 8.3× change. Any reasonable threshold detector will resolve that reliably.

---

## 2. The coil

Every physical parameter in this project is defined once in `config.py` and derived from the geometry below — nothing is asserted independently.

| Symbol | Quantity | Value |
|---|---|---|
| ri | Inner winding radius | 30 mm |
| ro | Outer winding radius | 40 mm |
| R | Mean radius | 35 mm |
| l | Winding length | 25 mm |
| c | Winding depth | 10 mm |
| — | Winding window | 250 mm² |
| — | Wire | 18 AWG, ⌀1.024 mm |
| a | Wire radius | 0.512 mm |
| p | Packing fraction | 0.7 |
| **N** | **Turns (derived)** | **212** |
| — | Actual copper fill | 0.6984 |
| d | Coil-to-coil separation | 164.06 mm |
| — | Model depth (into page) | 25 mm |

The turn count is **not** an input. It follows from how much 18 AWG wire fits in the winding window at the stated packing fraction:

$$N = \frac{p \cdot c \cdot l}{\pi a^2} = \frac{0.7 \times 2.500e-04}{8.2355e-07} = 212.49 \rightarrow 212$$

![Model geometry: rail cross-section, TX coil (right), RX coil (left), air domain.](C:/Users/rudra/Axle_counter/axlecounter_3dphysics/reports/figures/02_geometry.png)

---

## 3. Finite-element model

The model is solved in FEMM as a **2-D planar** problem: the drawn cross-section is extruded 25 mm into the page. That depth is what makes the reported fluxes and voltages absolute physical values rather than per-millimetre quantities.

| Setting | Value | Why |
|---|---|---|
| Solver | Time-harmonic | eddy currents in the rail + skin effect in copper |
| Frequency | 20 kHz | the operating point |
| Depth | 25 mm | the real coil's axial length |
| TX circuit | "New Circuit" (group 2) | energised, right/+x coil |
| RX circuit | "Receiver" (group 1) | open sense winding, left/−x coil |
| Coil material | "18 AWG" | magnet wire, fill 0.6984 |

> **Magnetostatic solving is wrong here.** At f = 0 the model reports *zero* induced RX voltage, because a static field induces nothing. Only a time-harmonic solve produces the physics an axle counter depends on.

![Solved flux map. Black contours are magnetic flux lines; the field originates at the energised TX coil.](C:/Users/rudra/Axle_counter/axlecounter_3dphysics/reports/figures/01_fem_flux_map.png)

---

## 4. Turn scaling — the model validating itself

Mutual inductance should scale as N², because both coils change together: N times the ampere-turns driving the flux, N times the linkage picking it up. Sweeping turns at fixed geometry tests that.

| Turns | M measured (µH) | M predicted by N² (µH) | Deviation |
|---|---|---|---|
| 50 | 1.1999 | 1.1940 | 0.50 % |
| 100 | 4.7922 | 4.7760 | 0.34 % |
| 150 | 10.7659 | 10.7459 | 0.19 % |
| 212 | 21.4651 | 21.4651 | 0.00 % |
| 300 | 42.8757 | 42.9838 | 0.25 % |
| 400 | 76.0246 | 76.4156 | 0.51 % |

The law holds to well under 1 % across an 8× range of turns. That is strong evidence the solver setup, the circuit definitions and the turn handling are all correct.

![Analytic M across turns and coil-area scale.](C:/Users/rudra/Axle_counter/axlecounter_3dphysics/reports/figures/03_mutual_inductance.png)

---

## 5. Frequency behaviour

M was measured at 21 points from 10 kHz to 20 kHz. It drifts by only **0.2 %** across the band.

A small, smooth drift is the expected signature of eddy currents in the steel rail growing with frequency. A jump or a discontinuity would indicate a broken solve.

---

## 6. Wheel detection

A steel block representing the wheel flange is placed in the coil-to-coil flux path and the model re-solved. The wheel provides a low-reluctance shunt and supports eddy currents, both of which divert flux away from the receiving coil.

| Condition | M (µH) | RX voltage (V) |
|---|---|---|
| No wheel | 21.4651 | 6.7435 |
| Wheel present | 2.5785 | 0.8101 |
| **Change** | **−87.99 %** | **−87.99 %** |

Wheel block: 64 × 100 mm of 1018 Steel, centred over the rail.

![Flux map with the wheel present. Compare with the clear-track map above.](C:/Users/rudra/Axle_counter/axlecounter_3dphysics/reports/figures/11_flux_with_wheel.png)

---

## 7. Geometry optimisation

A full-factorial sweep over coil shift and tilt was run (28 feasible solves, 7 rejected as unmeshable), and a quadratic response surface fitted to the result.

| Axis | Optimum | Note |
|---|---|---|
| Distance shift dx | -4.00 mm | quadratic term non-negative; fell back to best sampled point |
| Height shift dy | 0.00 mm | axis fixed in DOE |
| Tilt θ | -15.00° | clamped to sampled range |

The optimum yields **M = 31.9653 µH**, a **+48.9 %** change against the baseline 21.4651 µH.

> An optimum is only accepted if the fitted stationary point is a true maximum lying inside the sampled grid, and if it survives a live verification solve. Otherwise the best actually-sampled point is used, so the reported geometry is never an extrapolation.

---

## 8. Buildable design

Two identities set the design. The received signal is V_rx = ω·M·I, and the tuning capacitor sees V_cap = I·ω·L. Their ratio V_rx/V_cap = M/L is fixed by geometry, so adding turns raises signal and capacitor voltage together — **the capacitor's voltage rating is the binding constraint**.

| Cap class (V) | Turns | L (mH) | M (µH) | V_rx open (mV) | V_rx tuned (V) | C (nF) |
|---|---|---|---|---|---|---|
| 250 | 45 | 0.383 | 0.9671 | 607.7 | 60.77 | 165.19 |
| 630 | 72 | 0.981 | 2.4759 | 1555.6 | 155.56 | 64.53 |
| 1000 | 91 | 1.568 | 3.9550 | 2485.0 | 248.50 | 40.39 |
| 2000 | 129 | 3.150 | 7.9477 | 4993.7 | 499.37 | 20.10 |

**Recommended: the 1000 V class** — 91 turns, 18 AWG, L = 1.568 mH, C = 40.39 nF, tuned RX signal 248.50 V.

> **Resonance relocates voltage, it does not remove it.** Cancelling the coil's reactance drops the *supply* voltage to whatever the wire resistance needs — but the full reactive voltage now appears across the capacitor. Size that part for it.

---

## 9. Verification

An independent physics suite re-derives every published result from first principles and checks it against identities that must hold regardless of the model: **28 checks pass, 0 fail, 0 skip**.

What it verifies:

- Faraday's law V = ωΦ on every AC row of every CSV
- M independent of drive current (a linear magnetic model requires it)
- M ∝ N² turn scaling against the measured sweep
- the config anchor M0 matches the measured baseline row to within 1 %
- resonance identities C = 1/(ω²L) and V_cap = I·ω·L
- detection-dip arithmetic, and that the wheel *reduces* coupling
- the model's depth header matches the configured coil length
- an independent coil of known inductance, solved in FEMM and compared against Wheeler's formula

That last check is the strongest one: a coil whose inductance textbook physics already predicts is solved by the same solver, and the two agree to about 2 %. A full hand derivation is in `sanity_check.md`.

---

## 10. Limits and honest caveats

| Claim | Status |
|---|---|
| M ∝ N² turn scaling | **FEMM-verified** across 50–400 turns |
| Absolute M, V, dip % | **FEMM-measured** at the stated geometry |
| Linear-in-area scaling | **Extrapolation** — not solver-verified |
| Large area scale factors | Order-of-magnitude guidance only |
| Point-dipole hand estimate of M | Underestimates extended coils at modest d/R |
| Coil depth 25 mm | An assumption — set it to your real coil length |

> The one number to treat with suspicion is any result that scales the coil **area** far from the modelled geometry. Turn scaling is measured; area scaling is assumed.

---

## 11. Reproducing this

```bash
cd axlecounter_3dphysics
py -3 run_all.py
```

That runs every FEMM solve, both notebooks, all figures and the sanity suite in dependency order, then rebuilds this report from the results.


*Report generated by `build_report.py` from live project data. Prepared by Rudranarayan.*

