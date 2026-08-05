"""
Central configuration for the Axle Counter FEM / analytical study.

Every hardware parameter, path and identifier lives here, so the FEMM solver
scripts, the analytic models and the report/figure pipeline all read from ONE
place. Change a value here and every downstream script picks it up.

Two rules that keep this file trustworthy:
  * Nothing writes back to it. Computed results go to JSON/CSV in OUTPUT_DIR,
    so a config value is always an input, never a stale cached output.
  * Scripts live in subfolders (analysis_and_reporting/, optimization_and_design/,
    simulation_and_femm/) and must build paths from BASE_DIR / OUTPUT_DIR /
    FEM_FILE below rather than from their own __file__, which would resolve one
    level too deep.
"""
import os

# --- PATHS (portable: derived from this file's location) --------------------
# BASE_DIR is the project root because this file sits at the root.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FEM_FILE = os.path.join(BASE_DIR, "femm", "InternMadebyPratham.FEM")

# Every generated CSV / JSON / PNG lands here.
OUTPUT_DIR = os.path.join(BASE_DIR, "reports")
os.makedirs(OUTPUT_DIR, exist_ok=True)   # created on import, so no script has to

# --- OPERATING POINT (physics / hardware) -----------------------------------
# The base .FEM is stored as magnetostatic ([Frequency] = 0), but a real axle
# counter runs AC. Every solver script therefore sets the frequency itself --
# via femm_utils.set_frequency() or a direct mi_probdef(FREQUENCY_HZ, ...) --
# before calling mi_analyze(). Solving time-harmonic is what brings in eddy
# currents in the steel rail and skin effect in the copper; a magnetostatic
# solve reports zero induced RX voltage and understates coupling ~6x.
FREQUENCY_HZ = 20000.0        # 20 kHz operating frequency
TX_CURRENT_MAG = 2.5          # Primary excitation current, Amperes

# Axial length (into-the-page depth) of the REAL coil, millimetres.
#
# This is the most important scale factor in the project. The 2D planar FEMM
# model computes flux PER UNIT DEPTH, so this value multiplies every absolute
# flux / M / voltage the solver reports. Ratios (N^2 scaling, dip %, DOE
# trends) are unaffected by it; absolute numbers scale linearly.
#
# SET THIS TO YOUR PHYSICAL COIL LENGTH. 25 mm is an assumption chosen to match
# the sanity-check reference coil. It must also equal the [Depth] header inside
# the .FEM file -- sanity_check.py compares the two and fails if they disagree.
COIL_DEPTH_MM = 25.0

# --- COIL / CIRCUIT identifiers (as saved inside the FEMM file) --------------
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

# Block-label coordinates of the four coil halves in the CURRENT base file
# (mm, verified against [NumBlockLabels]).  (x, y, signed turns)
TX_LABELS = [(48.087341, 110.300000, +100), (70.294215, 107.291898, -100)]
RX_LABELS = [(-72.705741, 121.257318, +100), (-50.587341, 124.000000, -100)]
COIL_WIRE_BLOCK = "18 AWG"

# --- Steel "wheel" test block (mm) ------------------------------------------
# Cross-section of the passing wheel/flange dropped into the coil-to-coil flux
# path by femm_wheel_dip.py. Defined ONCE here because generate_wheel_figure.py
# draws the same rectangle -- if the two drifted apart the figure would show
# the wheel somewhere other than where it was actually solved.
WHEEL_X0, WHEEL_X1, WHEEL_Y0, WHEEL_Y1 = -32, 32, 150, 250

# --- Rotation centres for the DOE geometry moves (coil midpoints, mm) --------
TX_CENTER_X = (TX_LABELS[0][0] + TX_LABELS[1][0]) / 2.0
TX_CENTER_Y = (TX_LABELS[0][1] + TX_LABELS[1][1]) / 2.0
RX_CENTER_X = (RX_LABELS[0][0] + RX_LABELS[1][0]) / 2.0
RX_CENTER_Y = (RX_LABELS[0][1] + RX_LABELS[1][1]) / 2.0

# --- Design of Experiments (DOE) grid ---------------------------------------
distance_shifts = [-8, -4, 0, 4, 8]        # coils closer (-) or further (+)
height_shifts = [0]                        # height fixed per constraint
tilt_angles = [-15, -10, -5, 0, 5, 10, 15] # inward (-) / outward (+)

# --- VERIFIED FEMM BASELINE (analytic anchor) --------------------------------
# The single number every analytic model is scaled from. It is measured, not
# assumed: it is the Turns=100 row of reports/coil_parameter_sweep_femm.csv,
# solved time-harmonic at FREQUENCY_HZ with the model depth set to
# COIL_DEPTH_MM. Both coils carry BASELINE_TURNS turns.
# sanity_check.py re-reads that CSV and fails if M0_UH drifts from it by >1%,
# so if you re-solve the model, update this value to match.
BASELINE_TURNS = 100          # turns per coil (both TX and RX) in the base file
M0_UH = 0.926950              # mutual inductance at baseline, microhenries
M0_H = M0_UH * 1e-6           # same, henries

# Nominal per-coil cross-section, used when the analytic scripts turn an
# "area scale factor" into an absolute area. The 2D FEM coils are ~35 mm
# effective radius.
#
# CAVEAT, applies to every script that scales by area: M ~ N^2 (turns) IS
# verified against FEMM, but the linear-in-area term is an analytic
# EXTRAPOLATION that FEMM has NOT confirmed. Treat large area scale factors as
# order-of-magnitude design guidance only.
COIL_RADIUS_M = 0.035
A_REF_M2 = 3.1415926535 * COIL_RADIUS_M ** 2   # ~0.00385 m^2

# The optimised geometry is NOT stored here. axle.py writes its DOE result to
# reports/doe_rsm_result.json and apply_best_geom.py reads it from there, so
# there is exactly one live copy of the optimum and it cannot go stale against
# this file.
