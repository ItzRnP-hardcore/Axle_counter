"""
Central configuration for the Axle Counter FEM / analytical study.

EVERY physical, geometric and experimental parameter used anywhere in this
project is defined here, exactly once. No script may hardcode a coil dimension,
turn count, wire size, frequency or drive current -- if a number describes the
hardware, it belongs in this file and is imported from here.

Three rules that keep this file trustworthy:
  * Nothing writes back to it. Computed results go to JSON/CSV in OUTPUT_DIR,
    so a config value is always an input, never a stale cached output.
  * Values are DERIVED from stated assumptions wherever possible (see the coil
    block below). A derived value cannot silently drift out of step with the
    assumption it came from.
  * Scripts live in subfolders (analysis_and_reporting/, optimization_and_design/,
    simulation_and_femm/) and must build paths from BASE_DIR / OUTPUT_DIR /
    FEM_FILE below rather than from their own __file__, which would resolve one
    level too deep.
"""
import math
import os

# --- PATHS (portable: derived from this file's location) --------------------
# BASE_DIR is the project root because this file sits at the root.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FEM_FILE = os.path.join(BASE_DIR, "femm", "InternMadebyPratham.FEM")

# Every generated CSV / JSON / PNG lands here.
OUTPUT_DIR = os.path.join(BASE_DIR, "reports")
os.makedirs(OUTPUT_DIR, exist_ok=True)   # created on import, so no script has to

# =============================================================================
# CANONICAL COIL GEOMETRY
# =============================================================================
# The whole project describes ONE coil design: a short multilayer air-core
# solenoid. Everything below -- turn count, wire length, inductance, the FEMM
# model depth -- is derived from these five assumptions. Change an assumption
# here and every downstream number follows automatically.
#
#   ri = 30 mm   inner winding radius
#   ro = 40 mm   outer winding radius
#   l  = 25 mm   axial length of the winding
#   packing 0.70 fraction of the winding window actually filled with copper
#                (0.70 is a realistic round-wire figure: perfect hexagonal
#                 close packing is 0.9069, and a hand-wound multilayer coil
#                 with enamel insulation and layer-to-layer voids lands near
#                 0.65-0.75)
#   wire 18 AWG  bare copper, 1.024 mm diameter
#
# WHY THESE VALUES: they are the reference coil that sanity_check.py solves
# directly in FEMM (axisymmetric, no rail) and cross-checks against Wheeler's
# multilayer formula. Because that pair agrees to ~2%, this geometry is the one
# part of the project independently validated against textbook physics, which
# is why it was adopted as the canonical design for the whole folder.
COIL_INNER_RADIUS_M = 0.030    # ri
COIL_OUTER_RADIUS_M = 0.040    # ro
COIL_LENGTH_M = 0.025          # l, axial length of the winding
PACKING_FRACTION = 0.70        # copper fill fraction of the winding window

# --- Wire: 18 AWG, the single canonical conductor ---------------------------
# 18 AWG is the material already assigned to the coil blocks inside the .FEM
# file, and it is the gauge that makes the turn count below come out at 212.
# Any other gauge would change N, so the gauge and the turn count must be
# chosen together -- they are not independent knobs.
WIRE_AWG = 18
WIRE_DIAMETER_M = 1.024e-3
WIRE_RADIUS_M = WIRE_DIAMETER_M / 2.0            # 0.512 mm
WIRE_AREA_M2 = math.pi * WIRE_RADIUS_M ** 2      # bare copper cross-section
COIL_WIRE_BLOCK = "18 AWG"                       # FEMM material name

# --- Derived coil quantities ------------------------------------------------
COIL_RADIUS_M = (COIL_INNER_RADIUS_M + COIL_OUTER_RADIUS_M) / 2.0   # 0.035 m
COIL_BUILD_DEPTH_M = COIL_OUTER_RADIUS_M - COIL_INNER_RADIUS_M      # 0.010 m
WINDING_WINDOW_M2 = COIL_BUILD_DEPTH_M * COIL_LENGTH_M              # 2.5e-4 m^2
A_REF_M2 = math.pi * COIL_RADIUS_M ** 2                             # ~0.00385 m^2

# --- TURN COUNT (derived, not asserted) -------------------------------------
# How many 18 AWG turns fit in the winding window at the stated packing:
#
#     N = packing * (winding window area) / (wire cross-section area)
#       = 0.70 * (0.010 x 0.025) / (pi * 0.000512^2)
#       = 0.70 * 2.500e-4 / 8.2354e-7
#       = 212.49  ->  212 buildable turns
#
# CHANGED 2026-08-05: this project previously ran at 100 turns per coil, a
# value inherited from the original .FEM file with no stated justification.
# It has been changed to 212 so the turn count FOLLOWS FROM the coil geometry
# above instead of being an arbitrary input, making the FEM model, the analytic
# scripts and the hand calculations describe the same physical coil.
# The base .FEM block labels were rewritten +-100 -> +-212 to match
# (backup: old_files/pre_212turn_backup/InternMadebyPratham.FEM.100turn).
# Fill-factor check in the 2D model: each FEMM coil half has a 469.66 mm^2
# cross-section, so 212 turns of 18 AWG occupy 37.2% of it -- comfortably
# buildable (the reference coil's own window is tighter at 69.8%).
TURNS_EXACT = PACKING_FRACTION * WINDING_WINDOW_M2 / WIRE_AREA_M2    # 212.4948
BASELINE_TURNS = int(round(TURNS_EXACT))                             # 212

# Actual copper fill once the turn count is rounded to a buildable integer.
# Very slightly below PACKING_FRACTION because 212 < 212.4948. This is the
# value written into the .FEM material's <LamFill>, so the solver's AC
# eddy/proximity model sees the same winding density the geometry implies.
# (The model previously declared LamFill = 1, i.e. 100% solid copper, which
# contradicted the packing assumption.)
COIL_FILL_FACTOR = BASELINE_TURNS * WIRE_AREA_M2 / WINDING_WINDOW_M2  # 0.69837

# =============================================================================
# OPERATING POINT
# =============================================================================
# The base .FEM is stored as magnetostatic ([Frequency] = 0), but a real axle
# counter runs AC. Every solver script therefore sets the frequency itself --
# via femm_utils.set_frequency() or a direct mi_probdef(FREQUENCY_HZ, ...) --
# before calling mi_analyze(). Solving time-harmonic is what brings in eddy
# currents in the steel rail and skin effect in the copper; a magnetostatic
# solve reports zero induced RX voltage and understates coupling ~6x.
#
# 20 kHz is canonical across the ENTIRE project: the FEMM solves, the M0
# anchor, the 10-20 kHz frequency sweep and every analytic model.
FREQUENCY_HZ = 20000.0        # 20 kHz operating frequency
OMEGA = 2.0 * math.pi * FREQUENCY_HZ
TX_CURRENT_MAG = 2.5          # Primary excitation current, Amperes (peak)

# Material constants (single definition for every script).
MU0 = 4.0e-7 * math.pi        # permeability of free space, H/m
RHO_COPPER = 1.68e-8          # resistivity of copper, ohm.m at room temperature

# Axial length (into-the-page depth) of the REAL coil, millimetres.
#
# This is the most important scale factor in the project. The 2D planar FEMM
# model computes flux PER UNIT DEPTH, so this value multiplies every absolute
# flux / M / voltage the solver reports. Ratios (N^2 scaling, dip %, DOE
# trends) are unaffected by it; absolute numbers scale linearly.
#
# It is DERIVED from COIL_LENGTH_M so the planar model and the reference coil
# describe the same physical coil length. It must also equal the [Depth] header
# inside the .FEM file -- sanity_check.py compares the two and fails otherwise.
COIL_DEPTH_MM = COIL_LENGTH_M * 1000.0        # 25.0 mm

# =============================================================================
# COIL / CIRCUIT identifiers (as saved inside the FEMM file)
# =============================================================================
# Ground truth, read from the [NumBlockLabels] block of the base .FEM:
#   TX = "New Circuit" = FEMM group 2 = the RIGHT-hand (+x) coil, energised
#        with TX_CURRENT_MAG
#   RX = "Receiver"    = FEMM group 1 = the LEFT-hand  (-x) coil, open sense
#        winding (no source; its induced voltage is the output signal)
# Every script imports these rather than hardcoding the names, so renaming a
# circuit in FEMM only requires editing the two lines below.
TX_CIRCUIT = "New Circuit"    # energised circuit, carries TX_CURRENT_MAG
RX_CIRCUIT = "Receiver"       # open / sense circuit
TX_GROUP = 2                  # right-hand coil
RX_GROUP = 1                  # left-hand coil

# Block-label coordinates of the four coil halves in the base file (mm,
# verified against [NumBlockLabels]). Each coil is drawn as two halves carrying
# +N and -N turns (current down one side, back up the other), so the signed
# turn counts are derived from BASELINE_TURNS rather than written out.
#
# GEOMETRY REDRAWN 2026-08-05 so the FEM model matches the canonical coil:
#   * each conductor bundle is now COIL_BUILD_DEPTH_M x COIL_LENGTH_M
#     (10 x 25 mm = 250 mm^2), instead of the old 13.27 x 35.39 mm (469.65 mm^2)
#   * the two bundles of a coil are now 2 * COIL_RADIUS_M = 70 mm apart, giving
#     the canonical 35 mm mean radius; previously they were 22.12 mm apart,
#     implying an 11.06 mm radius that matched nothing else in the project
#   * each coil was translated outward so the inner bundle keeps its original
#     6.60 mm clearance from the rail head (which reaches x = 34.35 mm at coil
#     height). Without that move a 35 mm-radius coil would sit inside the rail.
# Consequence: coil-to-coil separation grew from ~120.8 mm to ~164.1 mm, so all
# absolute M/voltage values are LOWER than pre-redraw runs. Tilt angles and the
# vertical placement are unchanged.
# (backup: old_files/pre_212turn_backup/InternMadebyPratham.FEM.pre_redraw)
TX_LABELS = [(47.020400, 118.283900, +BASELINE_TURNS),
             (116.754000, 112.183000, -BASELINE_TURNS)]
RX_LABELS = [(-47.436100, 120.892100, +BASELINE_TURNS),
             (-116.914300, 112.361300, -BASELINE_TURNS)]

# Rotation centres for the DOE geometry moves (coil midpoints, mm).
TX_CENTER_X = (TX_LABELS[0][0] + TX_LABELS[1][0]) / 2.0
TX_CENTER_Y = (TX_LABELS[0][1] + TX_LABELS[1][1]) / 2.0
RX_CENTER_X = (RX_LABELS[0][0] + RX_LABELS[1][0]) / 2.0
RX_CENTER_Y = (RX_LABELS[0][1] + RX_LABELS[1][1]) / 2.0

# Centre-to-centre horizontal separation of the two coils (m), used by the
# analytic mutual-inductance estimates.
COIL_SEPARATION_M = abs(TX_CENTER_X - RX_CENTER_X) / 1000.0    # ~0.1208 m

# --- Steel "wheel" test block (mm) ------------------------------------------
# Cross-section of the passing wheel/flange dropped into the coil-to-coil flux
# path by femm_wheel_dip.py. Defined ONCE here because generate_wheel_figure.py
# draws the same rectangle -- if the two drifted apart the figure would show
# the wheel somewhere other than where it was actually solved.
WHEEL_X0, WHEEL_X1, WHEEL_Y0, WHEEL_Y1 = -32, 32, 150, 250
WHEEL_MATERIAL = "1018 Steel"
WHEEL_GROUP = 3

# =============================================================================
# SWEEP / STUDY GRIDS
# =============================================================================
# Design of Experiments grid for the geometry optimiser (axle.py).
distance_shifts = [-8, -4, 0, 4, 8]        # coils closer (-) or further (+)
height_shifts = [0]                        # height fixed per constraint
tilt_angles = [-15, -10, -5, 0, 5, 10, 15] # inward (-) / outward (+)

# Turn counts swept by femm_sweep.py and the analytic sweeps. BASELINE_TURNS
# MUST appear in this list: sanity_check.py validates M0_UH against the
# baseline row of the resulting CSV, and skips the check if it is absent.
TURNS_SWEEP = [50, 100, 150, BASELINE_TURNS, 300, 400]

# Drive currents swept by femm_sweep.py (A peak). Used to confirm M is
# independent of drive level, as a linear magnetic model requires.
CURRENT_SWEEP = [TX_CURRENT_MAG, 2.0 * TX_CURRENT_MAG]

# Frequencies swept by freq_sweep.py (Hz): 10 kHz to FREQUENCY_HZ in 500 Hz steps.
FREQ_SWEEP_START_HZ = 10000.0
FREQ_SWEEP_STEP_HZ = 500.0
FREQUENCY_SWEEP_HZ = [FREQ_SWEEP_START_HZ + i * FREQ_SWEEP_STEP_HZ
                      for i in range(int((FREQUENCY_HZ - FREQ_SWEEP_START_HZ)
                                         / FREQ_SWEEP_STEP_HZ) + 1)]

# Coil-area scale factors for the analytic extrapolation studies.
# CAVEAT: M ~ N^2 (turns) IS verified against FEMM, but the linear-in-area term
# is an analytic EXTRAPOLATION that FEMM has NOT confirmed. Treat scale factors
# above ~1 as order-of-magnitude design guidance only.
AREA_SCALE_SWEEP = [1.0, 5.0, 10.0, 15.0, 20.0]

# Maximum drive current the analytic studies are allowed to assume (A peak).
MAX_DRIVE_CURRENT_A = 5.0
# Maximum wire length per coil the optimisers may spend (m).
MAX_WIRE_LENGTH_M = 500.0
# Standard film-capacitor peak voltage classes the air-core design is sized to.
CAP_VOLTAGE_CLASSES = [250, 630, 1000, 2000]
# Capacitor class chosen as the recommended design point.
RECOMMENDED_CAP_VOLTAGE = 1000
# Realistic loaded Q of a solid-wire air coil at the operating frequency
# (proximity + dielectric losses; litz wire would do better).
Q_LOADED = 100.0

# =============================================================================
# VERIFIED FEMM BASELINE (analytic anchor)
# =============================================================================
# The single number every analytic model is scaled from. It is MEASURED, not
# assumed: it is the Turns = BASELINE_TURNS row of
# reports/coil_parameter_sweep_femm.csv, solved time-harmonic at FREQUENCY_HZ
# with the model depth set to COIL_DEPTH_MM. Both coils carry BASELINE_TURNS.
#
# sanity_check.py re-reads that CSV and FAILS if M0_UH drifts from it by >1%,
# so this value can never silently go stale. Re-measure it (run the pipeline)
# after changing turns, geometry, frequency or depth.
#
# Measured 2026-08-05 at BASELINE_TURNS = 212 turns, time-harmonic 20 kHz,
# depth 25 mm, on the REDRAWN geometry (35 mm coil radius, 10 x 25 mm bundles,
# LamFill = COIL_FILL_FACTOR).
#
# Do NOT try to reconcile this against older runs by scaling: the coil geometry
# itself changed. For reference, the value went 0.9269 uH (100 turns, 11.06 mm
# radius, 120.8 mm separation) -> 21.465 uH here. Turns alone account for
# ~4.5x; the rest is the coil radius growing 11.06 -> 35 mm, since M scales
# roughly as R^4 and that outweighs the separation growing 120.8 -> 164.1 mm.
# The measured number is authoritative; never back-calculate it.
M0_UH = 21.465146             # mutual inductance at baseline, microhenries
M0_H = M0_UH * 1e-6           # same, henries

# --- Analytic "scaled-up" design point --------------------------------------
# summary.py and physics_calculation.ipynb explore a larger coil aimed at a
# 3.3 Vpp secondary. That design point is expressed as a SCALE FACTOR on the
# canonical coil rather than as an independent absolute area, so it can never
# drift away from the geometry above. The scale is capped at the largest value
# in AREA_SCALE_SWEEP so the study stays inside the range actually swept.
DESIGN_TURNS = BASELINE_TURNS
DESIGN_AREA_SCALE = 20.0
DESIGN_AREA_M2 = A_REF_M2 * DESIGN_AREA_SCALE
DESIGN_TARGET_VPP = 3.3       # target secondary peak-to-peak voltage

# The optimised geometry is NOT stored here. axle.py writes its DOE result to
# reports/doe_rsm_result.json and apply_best_geom.py reads it from there, so
# there is exactly one live copy of the optimum and it cannot go stale against
# this file.
