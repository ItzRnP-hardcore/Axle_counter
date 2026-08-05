"""Print the cross-section area of one TX coil half.

Solves the model, selects the first TX coil-half block and reports its area,
which the analytic scripts use as a sanity check on their assumed coil size.

Works on a scratch copy: FEMM auto-saves the open document when it analyzes,
so analyzing the base file in place would silently mutate it. Paths come from
config (BASE_DIR / FEM_FILE), not this script's own directory, because the
script lives in a subfolder.
"""
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import femm
import config
from simulation_and_femm import femm_utils

femm.openfemm()
try:
    # Copy the base model to a scratch file and set the AC operating point.
    femm_utils.open_scratch("_area_work.fem")
    # Mesh and solve (window hidden), then open the solution for post-processing.
    femm.mi_analyze(1)
    femm.mi_loadsolution()
    # Select the first TX coil-half by clicking its block label at the position
    # recorded in config, which describes the geometry as currently saved.
    x, y, _ = config.TX_LABELS[0]
    femm.mo_selectblock(x, y)
    # mo_blockintegral computes an integral over the selected blocks; integral
    # type 5 is the block cross-section area.
    area = femm.mo_blockintegral(5)   # 5 = block cross-section area
    print(f"TX coil-half area: {area} m^2")
    femm.mo_close()
    femm.mi_close()
finally:
    femm.closefemm()
