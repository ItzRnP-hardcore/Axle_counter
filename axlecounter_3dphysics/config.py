"""
Central configuration for the Axle Counter FEM / analytical study.

Everything hardware-related lives here so the FEMM scripts, the analytical
models and the report pipeline all read from ONE place. Change a value here
and every downstream script picks it up -- no more editing hard-coded paths
or magic numbers scattered across files.
"""
import os

# --- PATHS (portable: derived from this file's location) --------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FEM_FILE = os.path.join(BASE_DIR, "femm", "InternMadebyPratham.FEM")

# All generated CSVs / images go here (was previously a hard-coded .gemini path)
OUTPUT_DIR = os.path.join(BASE_DIR, "reports")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# --- OPERATING POINT (physics / hardware) -----------------------------------
# NOTE: the base .FEM is currently saved as magnetostatic (Frequency = 0).
# A real axle counter runs AC. Set the intended excitation frequency here and
# use femm_utils.set_frequency() before mi_analyze() to switch the solver to
# time-harmonic mode (captures eddy currents in the steel rail + skin effect).
FREQUENCY_HZ = 20000.0        # 20 kHz operating frequency
TX_CURRENT_MAG = 2.5          # Primary excitation current, Amperes

# --- COIL / CIRCUIT identifiers (as named inside the FEMM file) -------------
# The FEMM file uses these two circuit names. Centralised so a rename only
# has to happen in one spot.
TX_CIRCUIT = "New Circuit"    # circuit physically carrying TX_CURRENT_MAG
RX_CIRCUIT = "Receiver"       # open / sense circuit

# Block-label coordinates of the four coil halves (mm), used by sweeps.
TX_LABELS = [(-89.1, 120.9), (-64.1, 124.0)]   # group 1
RX_LABELS = [(61.6, 110.3), (86.7, 106.9)]     # group 2
COIL_WIRE_BLOCK = "18 AWG"

# --- Rotation centres for the DOE geometry moves ----------------------------
TX_CENTER_X, TX_CENTER_Y = -64.1, 124.0
RX_CENTER_X, RX_CENTER_Y = 61.6, 110.3

# --- Design of Experiments (DOE) grid ---------------------------------------
distance_shifts = [-8, -4, 0, 4, 8]        # coils closer (-) or further (+)
height_shifts = [0]                        # height fixed per constraint
tilt_angles = [-15, -10, -5, 0, 5, 10, 15] # inward (-) / outward (+)

# --- Results appended automatically by the optimisation scripts -------------
# The baseline mutual inductance is calculated for 100 turns per coil.
BASELINE_TURNS = 100
OPTIMAL_M_uH = 0.00771182593163102
OPTIMAL_X = -15.273096737661167
OPTIMAL_Y = 0
OPTIMAL_THETA = 0.45497083075631695

SCALED_M_uH = 0.00771182593163102
SCALED_FACTOR = 1.5
