"""
Central configuration for the Axle Counter FEM / analytical study.

Everything hardware-related lives here so the FEMM scripts, the analytical
models and the report pipeline all read from ONE place. Change a value here
and every downstream script picks it up -- no more editing hard-coded paths
or magic numbers scattered across files.

Scripts must NOT append results to this file (that created duplicate keys and
CWD-dependent writes). Computed results go to JSON/CSV files in OUTPUT_DIR.
"""
import os

# --- PATHS (portable: derived from this file's location) --------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FEM_FILE = os.path.join(BASE_DIR, "femm", "InternMadebyPratham.FEM")

# All generated CSVs / images go here (was previously a hard-coded .gemini path)
OUTPUT_DIR = os.path.join(BASE_DIR, "reports")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# --- OPERATING POINT (physics / hardware) -----------------------------------
# NOTE: the base .FEM is saved as magnetostatic (Frequency = 0). A real axle
# counter runs AC. Every solver script must call femm_utils.set_frequency()
# (or mi_probdef with FREQUENCY_HZ) before mi_analyze() so the solve is
# time-harmonic (eddy currents in the steel rail + skin effect).
FREQUENCY_HZ = 20000.0        # 20 kHz operating frequency
TX_CURRENT_MAG = 2.5          # Primary excitation current, Amperes

# Axial length (into-the-page depth) of the REAL coil, millimetres. The 2D
# planar FEMM model computes flux per unit depth, so this directly scales
# every absolute flux / M / voltage the solver reports (ratios are
# unaffected). Historically the model ran with Depth = 1 mm, which made all
# absolute numbers 25x too small. SET THIS TO YOUR PHYSICAL COIL LENGTH --
# 25 mm is an assumption matching the sanity-check reference coil.
COIL_DEPTH_MM = 25.0

# --- COIL / CIRCUIT identifiers (as saved inside the FEMM file) --------------
# In the CURRENT base .FEM the energised circuit ("New Circuit", 2.5 A) sits on
# the RIGHT-hand coil, which is FEMM group 2; the open sense circuit
# ("Receiver") is the LEFT-hand coil, group 1. Historical comments assumed the
# opposite -- trust these constants, not old comments.
TX_CIRCUIT = "New Circuit"    # energised circuit, carries TX_CURRENT_MAG
RX_CIRCUIT = "Receiver"       # open / sense circuit
TX_GROUP = 2                  # right-hand coil
RX_GROUP = 1                  # left-hand coil

# Block-label coordinates of the four coil halves in the CURRENT base file
# (mm, verified against [NumBlockLabels]).  (x, y, signed turns)
TX_LABELS = [(48.087341, 110.300000, +100), (70.294215, 107.291898, -100)]
RX_LABELS = [(-72.705741, 121.257318, +100), (-50.587341, 124.000000, -100)]
COIL_WIRE_BLOCK = "18 AWG"

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
# From the property-based sweep of the CURRENT geometry at FREQUENCY_HZ and
# COIL_DEPTH_MM (reports/coil_parameter_sweep_femm.csv, Turns=100 row). Both
# coils carry BASELINE_TURNS turns. All analytic scaling laws anchor here.
# (The pre-depth-fix anchor was 0.037078 uH at the old 1 mm model depth.)
BASELINE_TURNS = 100          # turns per coil (both TX and RX) in the base file
M0_UH = 0.926950              # mutual inductance at baseline, microhenries
M0_H = M0_UH * 1e-6           # same, henries

# Nominal per-coil cross-section used when the analytic scripts express an
# "area scale" as an absolute area. The 2D FEM coils are ~35 mm effective
# radius; this is an estimate, and the linear-in-area M scaling law is an
# EXTRAPOLATION, not a FEMM result -- treat large area scales with caution.
COIL_RADIUS_M = 0.035
A_REF_M2 = 3.1415926535 * COIL_RADIUS_M ** 2   # ~0.00385 m^2

# --- Historical DOE results (STALE -- kept for reference only) ---------------
# Produced by an old axle.py run that solved MAGNETOSTATIC (f=0) on the
# PRE-MOVE geometry, with the optimum extrapolated outside the sampled range.
# Do not anchor new analytics on these numbers; use M0_UH above.
OPTIMAL_M_uH = 0.00771182593163102   # stale (DC solve, old geometry)
OPTIMAL_X = -15.273096737661167      # stale (outside the sampled +/-8 mm)
OPTIMAL_Y = 0
OPTIMAL_THETA = 0.45497083075631695
SCALED_M_uH = 0.00771182593163102    # stale (the 1.5x scale never took effect)
SCALED_FACTOR = 1.5
