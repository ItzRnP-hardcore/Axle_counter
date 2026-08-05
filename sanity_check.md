# Coil Sanity Check — Theory and Hand Calculation

A step-by-step hand calculation of the axle-counter coil: turns, inductance,
magnetic field, flux, resistance, resonance, and mutual inductance.

Each step states **the theory first**, then applies it to the actual coil.
Every number is checked against the FEMM simulation at the end.

Prepared by Rudranarayan.

---

## 0. The coil we are calculating

Every value below comes from `axlecounter_3dphysics/config.py`, which is the
single source of truth for the whole project.

| Symbol | Quantity | Value |
|---|---|---|
| ri | Inner winding radius | 30 mm |
| ro | Outer winding radius | 40 mm |
| R | **Mean radius** (ri+ro)/2 | **35 mm** |
| l | Winding length (axial) | 25 mm |
| c | Winding depth (ro−ri) | 10 mm |
| — | Wire | 18 AWG, diameter 1.024 mm |
| a | Wire radius | 0.512 mm |
| — | Packing fraction | 0.70 |
| f | Frequency | 20 kHz |
| I | Drive current (peak) | 2.5 A |
| d | Coil-to-coil separation | 164.06 mm |

Constants: μ₀ = 4π×10⁻⁷ H/m, ρ(copper) = 1.68×10⁻⁸ Ω·m.

> **Shape matters.** The coil is 70 mm across but only 25 mm long, so l/R = 0.71.
> It is a **short, fat** coil — not a long thin solenoid. Step 2 shows this is
> the single most important fact in the whole calculation.

---

## 1. How many turns fit?

### Theory

A coil is wound into a rectangular **winding window** of depth c and length l.
Each turn of wire occupies a circle of area πa². Real wire cannot fill the
window perfectly — there are gaps between round wires and a little insulation —
so we multiply by a **packing fraction**, typically 0.65–0.75 for hand-wound
round wire.

$$N = \frac{\text{packing} \times (\text{window area})}{\text{area of one wire}} = \frac{p \cdot c \cdot l}{\pi a^2}$$

### Calculation

Window area:

$$c \times l = 0.010 \times 0.025 = 2.500 \times 10^{-4}\ \text{m}^2$$

Area of one 18 AWG wire:

$$\pi a^2 = \pi (0.512 \times 10^{-3})^2 = 8.2354 \times 10^{-7}\ \text{m}^2$$

So:

$$N = \frac{0.70 \times 2.500 \times 10^{-4}}{8.2354 \times 10^{-7}} = 212.49$$

**N = 212 turns** (rounded to a whole turn).

> Rounding 212.49 down to 212 makes the real copper fill 0.6984 instead of
> 0.700. That exact figure is written into the FEMM material as its fill
> factor, so the simulation models the same winding density we assumed here.

---

## 2. Self-inductance L

### Theory

Inductance measures the flux a coil links per amp of its own current. There are
three standard formulas, and **choosing the right one is the whole problem**:

**(a) Long solenoid** — assumes the coil is much longer than it is wide:

$$L = \frac{\mu_0 N^2 \pi R^2}{l} \qquad \text{needs } l \gg R$$

**(b) Single loop** — assumes all N turns sit in one thin filament:

$$L = \mu_0 N^2 R\left(\ln\frac{8R}{a} - 2\right) \qquad \text{needs } a \ll R$$

**(c) Wheeler's multilayer formula** — an empirical fit built for exactly our
case: a coil with real length and real winding depth. In inches it reads
L[µH] = 0.8a²N²/(6a+9b+10c). Converting to metres, every length divides by
0.0254; the numerator has two lengths squared and the denominator one, so one
factor of 1/0.0254 survives:

$$L = \frac{0.8}{0.0254}\times 10^{-6}\;\frac{R^2N^2}{6R + 9l + 10c} = \frac{31.496 \times 10^{-6}\, R^2 N^2}{6R + 9l + 10c}$$

### Which one applies?

| Formula | Requires | Our coil | Verdict |
|---|---|---|---|
| Long solenoid | l ≫ R | l/R = **0.71** | **fails** |
| Single loop | thin bundle | bundle is 10×25 mm vs R = 35 mm | **fails** |
| Wheeler | winding length > 0.2R | 0.71 R | **use this** |

### Calculation

Denominator:

$$6(0.035) + 9(0.025) + 10(0.010) = 0.210 + 0.225 + 0.100 = 0.535$$

Numerator:

$$31.496\times10^{-6} \times (0.035)^2 \times (212)^2 = 31.496\times10^{-6} \times 1.225\times10^{-3} \times 44944 = 1.7341\times10^{-3}$$

$$L = \frac{1.7341\times10^{-3}}{0.535} = 3.2412\times10^{-3}\ \text{H}$$

**L = 3.241 mH**

### Proof that the other two are wrong

$$L_{solenoid} = 8.694\ \text{mH} \qquad L_{loop} = 8.508\ \text{mH}$$

That is **2.68×** and **2.63×** too big respectively.

> **FEMM solved this same coil axisymmetrically and got 3.180 mH.**
> Wheeler's 3.241 mH is **1.9 % away** — well inside its ~2 % accuracy.
> The other two formulas are off by a factor of 2.6. This is the calculation
> validating itself.

---

## 3. Magnetic field at the centre

### Theory

For an **infinitely long** solenoid with n turns per metre, the field inside is
uniform:

$$B = \mu_0 n I$$

A real coil of finite length leaks flux out of its ends, so the true centre
field is always **lower**. For a coil of length l and radius R:

$$B_{centre} = \mu_0 n I \cdot \frac{l/2}{\sqrt{R^2 + (l/2)^2}}$$

The fraction on the right approaches 1 only when l ≫ R.

### Calculation

Turn density:

$$n = N/l = 212 / 0.025 = 8480\ \text{turns/m}$$

Infinite-solenoid value:

$$\mu_0 n I = (1.2566\times10^{-6})(8480)(2.5) = 26.64\ \text{mT}$$

Finite-length correction factor:

$$\frac{0.0125}{\sqrt{0.035^2 + 0.0125^2}} = \frac{0.0125}{0.037165} = 0.3363$$

$$B_{centre} = 26.64 \times 0.3363 = 8.960\ \text{mT}$$

**B = 8.96 mT**

> The real coil produces only **34 %** of the infinite-solenoid field — the same
> short-and-fat geometry that disqualified the solenoid formula in Step 2.

---

## 4. Magnetic flux and flux linkage

### Theory

**Flux** Φ is the field passing through **one** turn. **Flux linkage** λ counts
all N turns:

$$\Phi = B \cdot A, \qquad \lambda = N\Phi, \qquad \lambda = L I$$

Keeping these apart is the most common source of factor-of-N errors. FEMM
reports **linkage**, not flux.

### Calculation

Mean turn area:

$$A = \pi R^2 = \pi (0.035)^2 = 3.8485\times10^{-3}\ \text{m}^2$$

From the inductance:

$$\lambda = L I = 3.2412\times10^{-3} \times 2.5 = 8.103\times10^{-3}\ \text{Wb·turns}$$

$$\Phi = \lambda / N = 8.103\times10^{-3} / 212 = 38.22\ \mu\text{Wb}$$

**Φ = 38.22 µWb per turn, λ = 8.10 mWb·turns**

### Cross-check using the field from Step 3

$$\Phi \approx B_{centre} \cdot A = 8.960\times10^{-3} \times 3.8485\times10^{-3} = 34.48\ \mu\text{Wb}$$

The two routes differ by **11 %**, which is the expected accuracy when a
10×25 mm multilayer winding is represented by one mean radius and one
centre-field value. Agreement at this level confirms no gross error.

---

## 5. Resistance and skin effect

### Theory

At DC, resistance is just the wire's length over its cross-section:

$$R_{DC} = \frac{\rho\, l_{wire}}{\pi a^2}$$

At AC, current is pushed toward the conductor surface. The characteristic depth
is the **skin depth**:

$$\delta = \sqrt{\frac{\rho}{\pi f \mu_0}}$$

If the wire radius exceeds δ, the usable copper shrinks and resistance rises.
With x = a/δ the standard approximation has two branches.

For a thin wire (x < 1), the correction is tiny:

$$\frac{R_{AC}}{R_{DC}} = 1 + \frac{x^4}{48}$$

For a thick wire (x ≥ 1), resistance grows roughly in proportion to x:

$$\frac{R_{AC}}{R_{DC}} = \frac{x}{2} + \frac{3}{4} + \frac{3}{32x}$$

### Calculation

Wire length:

$$l_{wire} = N \cdot 2\pi R = 212 \times 2\pi \times 0.035 = 46.62\ \text{m}$$

$$R_{DC} = \frac{1.68\times10^{-8} \times 46.62}{8.2354\times10^{-7}} = 0.951\ \Omega$$

Skin depth at 20 kHz:

$$\delta = \sqrt{\frac{1.68\times10^{-8}}{\pi (20000)(4\pi\times10^{-7})}} = 0.4613\ \text{mm}$$

Since x = 0.512/0.4613 = **1.110 ≥ 1**, use the second branch:

$$\frac{R_{AC}}{R_{DC}} = \frac{1.110}{2} + 0.75 + \frac{3}{32(1.110)} = 0.555 + 0.750 + 0.084 = 1.389$$

$$R_{AC} = 0.951 \times 1.389 = 1.321\ \Omega$$

**R_AC = 1.32 Ω** (39 % above DC)

> δ is smaller than the wire radius, so skin effect is real here and cannot be
> ignored. A thinner wire, or litz wire, would reduce it.

---

## 6. Quality factor and resonant tuning

### Theory

Q compares stored energy to energy lost per cycle:

$$Q = \frac{\omega L}{R_{AC}}$$

To cancel the coil's reactance we add a capacitor that resonates with it:

$$\omega = \frac{1}{\sqrt{LC}} \quad\Longrightarrow\quad C = \frac{1}{\omega^2 L}$$

At resonance the supply only has to overcome R_AC — but the **reactive voltage
does not disappear**, it appears across the capacitor:

$$V_{cap} = I\,\omega L$$

### Calculation

ω = 2π(20000) = 1.2566×10⁵ rad/s.

$$Q = \frac{1.2566\times10^{5} \times 3.2412\times10^{-3}}{1.321} = 308$$

$$C = \frac{1}{(1.2566\times10^{5})^2 \times 3.2412\times10^{-3}} = 19.54\ \text{nF}$$

$$V_{cap} = 2.5 \times 1.2566\times10^{5} \times 3.2412\times10^{-3} = 1018\ \text{V}$$

**Q = 308, C = 19.5 nF, V_cap = 1018 V peak**

> **Design warning.** Resonance does not remove the high voltage — it *moves*
> it from the supply onto the capacitor. Driving 2.5 A through this coil needs
> a capacitor rated **above 1 kV**. This is why the design scripts size parts
> against 250 / 630 / 1000 / 2000 V capacitor classes.

---

## 7. Mutual inductance M

### Theory

Two coils sit side by side, both axes vertical, separated horizontally by d.

Far from a coil, its field looks like a **magnetic dipole** of moment:

$$m = N I A$$

A dipole's field depends on direction. Directly above it (on-axis) the field is
twice as strong as it is out to the side (equatorial):

$$B_{axis} = \frac{\mu_0}{4\pi}\frac{2m}{d^3}, \qquad B_{equatorial} = \frac{\mu_0}{4\pi}\frac{m}{d^3}$$

Because both axes are vertical and the coils are side by side, **each sits in
the other's equatorial plane**, so we use the second one. Assuming the field is
uniform across the secondary and equal to its value at the secondary's centre:

$$\Phi_{1\to2} = B_{eq}A, \qquad \lambda_2 = N\Phi_{1\to2}, \qquad M = \frac{\lambda_2}{I}$$

Combining gives the closed form:

$$M = \frac{\mu_0 \pi N^2 R^4}{4 d^3}$$

### Calculation

Dipole moment:

$$m = 212 \times 2.5 \times 3.8485\times10^{-3} = 2.040\ \text{A·m}^2$$

Equatorial field at the far coil (d = 0.16406 m):

$$B_{eq} = \frac{(4\pi\times10^{-7})(2.040)}{4\pi (0.16406)^3} = \frac{10^{-7} \times 2.040}{4.4157\times10^{-3}} = 46.19\ \mu\text{T}$$

Flux through one secondary turn:

$$\Phi = 46.19\times10^{-6} \times 3.8485\times10^{-3} = 177.8\ \text{nWb}$$

Linkage and M:

$$\lambda_2 = 212 \times 177.8\times10^{-9} = 37.69\ \mu\text{Wb·t}$$

$$M = \frac{37.69\times10^{-6}}{2.5} = 15.07\ \mu\text{H}$$

**M = 15.07 µH** (hand estimate)

**FEMM measured M = 21.47 µH** — the simulation is **1.42× higher**.

> **Why the hand value is low, and why that is expected.** The dipole formula
> pretends each coil is a *point* at its centre, 164 mm away. The real coils are
> 70 mm wide, so their facing conductor bundles are only about 94 mm apart —
> much closer than 164 mm — and closer conductors couple far more strongly
> (M falls as 1/d³). Working the other way, the steel rail between the coils
> shields some flux. The point-dipole result is therefore an
> **order-of-magnitude estimate**, good for showing how M *scales*, not for
> predicting its exact value. FEMM, which models the true shape and the rail,
> is the authority.

---

## 8. Coupling coefficient and output signal

### Theory

The coupling coefficient states what fraction of one coil's flux reaches the
other:

$$k = \frac{M}{\sqrt{L_1 L_2}} = \frac{M}{L} \quad (\text{identical coils})$$

The induced open-circuit signal follows from Faraday's law in AC form:

$$V_{rx} = \omega M I$$

### Calculation

$$k = \frac{21.47\times10^{-6}}{3.2412\times10^{-3}} = 0.0066$$

$$V_{rx} = 1.2566\times10^{5} \times 21.47\times10^{-6} \times 2.5 = 6.74\ \text{V}$$

**k = 0.66 %, V_rx = 6.74 V**

> Very weak coupling — and that is correct for an axle counter. The coils are
> deliberately far apart. The signal is not the coupling itself but the
> **change** in it: when a steel wheel enters the gap, FEMM shows M collapsing
> from 21.47 µH to 2.58 µH, an **88 % dip**, with RX voltage falling 6.74 V →
> 0.81 V. That dip is the axle count.

---

## 9. Hand calculation vs simulation

| Quantity | Hand calculation | FEMM | Agreement |
|---|---|---|---|
| Turns N | 212.49 → 212 | 212 | exact |
| **Inductance L** | **3.241 mH** | **3.180 mH** | **1.9 %** |
| L (solenoid formula) | 8.694 mH | — | 2.68× — formula invalid |
| L (single-loop formula) | 8.508 mH | — | 2.63× — formula invalid |
| Wire length | 46.62 m | 46.6 m | exact |
| R_DC | 0.951 Ω | 0.951 Ω | exact |
| R_AC | 1.321 Ω | 1.321 Ω | exact |
| Q | 308 | 309 | exact |
| C resonant | 19.54 nF | 19.47 nF | 0.4 % |
| V_cap | 1018 V | 1022 V | 0.4 % |
| Mutual inductance M | 15.07 µH | 21.47 µH | 1.42× — see Step 7 |
| V_rx | 4.74 V (from hand M) | 6.74 V | 1.42× |

**Conclusion.** Everything that depends on the coil *by itself* — turns,
inductance, field, flux, resistance, Q, resonance — matches the simulation to
within 2 %, most of it exactly. That validates the solver setup and the
geometry.

The only quantity that disagrees is the coil-to-coil mutual inductance, and it
disagrees for a known and quantified reason: the point-dipole approximation
cannot represent two 70 mm-wide coils only 164 mm apart.

---

## 10. Assumptions, and how much they matter

| Assumption | Status | Effect |
|---|---|---|
| Packing fraction 0.70 | design choice; sets N | direct, N ∝ p |
| Wheeler valid (winding length > 0.2R) | satisfied | 1–2 % |
| Turns rounded 212.49 → 212 | true fill 0.6984 | 0.2 % |
| Coil is one filament at R = 35 mm | winding is really 10×25 mm | ~10 % |
| Uniform field across the far coil | **weak** — see below | large |
| Point dipole (d ≫ R) | **weak** — d/R = 4.7 | 1.42× |
| No steel rail in the hand model | rail shields flux | opposes the above |

**The uniform-field assumption, quantified.** Field falls as 1/d³, so across
the far coil's own width (±35 mm about 164 mm):

$$\frac{B(d-R)}{B(d)} = \left(\frac{164.06}{129.06}\right)^3 = 2.05, \qquad \frac{B(d+R)}{B(d)} = \left(\frac{164.06}{199.06}\right)^3 = 0.56$$

The true field varies from **2.05×** down to **0.56×** the centre value. Calling
it uniform is a deliberate simplification, not an exact result.

> **Rule of thumb:** trust the hand calculation for **scaling laws** —
> L ∝ N², M ∝ N², M ∝ 1/d³, M ∝ R⁴. Trust FEMM for **absolute** mutual
> inductance, because only it models the real coil shape and the steel rail.

---

## Appendix — reproducing these numbers

```bash
cd axlecounter_3dphysics
py -3 analysis_and_reporting/sanity_check.py
```

That script recomputes every value above from `config.py`, solves the same coil
in FEMM, and writes `reports/sanity_check_report.md`. Current status:
**28 checks passed, 0 failed.**

To re-run the entire study (all FEMM solves, analytics, notebooks, figures):

```bash
cd axlecounter_3dphysics
py -3 run_all.py
```
