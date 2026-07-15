import os

# --- CONFIGURATION ---
# Base directory of the project
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Point this to the location of your prepared FEMM file
FEM_FILE = os.path.join(BASE_DIR, "femm", "InternMadebyPratham.FEM")

# Define the centers of rotation for your coils
TX_CENTER_X = -64.1
TX_CENTER_Y = 124.0
RX_CENTER_X = 61.6
RX_CENTER_Y = 110.3

# Design of Experiments (DOE) Grid
distance_shifts = [-8, -4, 0, 4, 8]  # Moving coils closer (-) or further (+)
height_shifts = [0]    # Height fixed as per user constraint
tilt_angles = [-15, -10, -5, 0, 5, 10, 15]      # Tilting inwards (-) or outwards (+)

# Circuit parameters
TX_CURRENT_MAG = 2.5 # Current in Amperes

# Automatically added by axle.py
OPTIMAL_M_uH = 0.00771182593163102
OPTIMAL_X = -15.273096737661167
OPTIMAL_Y = 0
OPTIMAL_THETA = 0.45497083075631695

# New Geometry Base M from FEMM (Scale 1.5x)
SCALED_M_uH = 0.00771182593163102
SCALED_FACTOR = 1.5
