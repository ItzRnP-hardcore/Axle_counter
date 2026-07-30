"""Print the cross-section area of one TX coil half.

Works on a scratch copy: FEMM auto-saves on analyze, so analyzing the base
file in place (as the old version did) silently mutates it.
"""
import femm
import config
import femm_utils

femm.openfemm()
try:
    femm_utils.open_scratch("_area_work.fem")
    femm.mi_analyze(1)
    femm.mi_loadsolution()
    # Select the first TX coil-half label at its CURRENT position (the old
    # version reconstructed a pre-move position from stale config values).
    x, y, _ = config.TX_LABELS[0]
    femm.mo_selectblock(x, y)
    area = femm.mo_blockintegral(5)   # 5 = block cross-section area
    print(f"TX coil-half area: {area} m^2")
    femm.mo_close()
    femm.mi_close()
finally:
    femm.closefemm()
