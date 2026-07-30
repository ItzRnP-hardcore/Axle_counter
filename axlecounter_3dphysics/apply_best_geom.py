"""
Apply a geometry move + scale to the coil pair and measure the resulting M.

HISTORY / WARNING
-----------------
The original version of this script OVERWROTE the base .FEM file with the
(extrapolated, DC-fit) optimum from the old axle.py, and its 1.5x mi_scale
call silently failed -- config's SCALED_M_uH ended up identical to
OPTIMAL_M_uH. The base file HAS ALREADY BEEN MOVED once by that script, so
re-applying a shift on top would double-shift the coils.

This version:
  * NEVER touches the base file -- output goes to femm/optimal_geom_scaled.fem.
  * Reads the shift from reports/doe_rsm_result.json (produced by the fixed
    axle.py, which solves AC and clamps the optimum to the sampled range).
    If that file does not exist it refuses to run rather than reusing the
    stale config.OPTIMAL_* values.
  * Passes the editaction argument to mi_scale (4 = selected group) so the
    scale actually applies, and sanity-checks that M changed afterwards.
  * Appends results to reports/scaled_geom_result.json, not config.py.
"""
import json
import os

import femm

import config
import femm_utils

RESULT_IN = os.path.join(config.OUTPUT_DIR, "doe_rsm_result.json")
RESULT_OUT = os.path.join(config.OUTPUT_DIR, "scaled_geom_result.json")
OUT_FILE = os.path.join(config.BASE_DIR, "femm", "optimal_geom_scaled.fem")

# Candidate scale factors, tried largest-first; the first one whose scaled
# geometry still meshes (no collision with the rail) wins. 1.5x was chosen
# for the old pre-2026 optimum and no longer fits at the corrected optimum.
SCALE_CANDIDATES = [1.5, 1.4, 1.3, 1.2, 1.1, 1.0]


def measure_M():
    """Return M in uH, or None if the geometry cannot be meshed/solved."""
    try:
        femm.mi_analyze(1)
        femm.mi_loadsolution()
    except Exception as e:
        print(f"   (unsolvable geometry: {e})")
        return None
    M_uH, _, _, _ = femm_utils.extract_mutual_inductance()
    femm.mo_close()
    return M_uH


def move_coils(dx, dy, dtheta, scale):
    """Apply shift + tilt + scale to both coils on the open document.

    NOTE: FEMM clears the selection after every move/rotate/scale operation,
    so the group must be re-selected before EACH operation -- this is why the
    original script's mi_scale silently did nothing. mi_scale is called via
    raw LUA (editaction 4 = selected group) to avoid the pyfemm comma bug.
    """
    for group, sx, sth in ((config.RX_GROUP, -1, +1), (config.TX_GROUP, +1, -1)):
        cx0 = config.RX_CENTER_X if group == config.RX_GROUP else config.TX_CENTER_X
        cy0 = config.RX_CENTER_Y if group == config.RX_GROUP else config.TX_CENTER_Y
        femm.mi_clearselected()
        femm.mi_selectgroup(group)
        femm.mi_movetranslate(sx * dx, dy)
        cx, cy = cx0 + sx * dx, cy0 + dy
        femm.mi_clearselected()
        femm.mi_selectgroup(group)
        femm.mi_moverotate(cx, cy, sth * dtheta)
        if scale != 1.0:
            femm.mi_clearselected()
            femm.mi_selectgroup(group)
            femm.callfemm(f"mi_scale({cx},{cy},{scale},4)")
    femm.mi_clearselected()


def main():
    if not os.path.exists(RESULT_IN):
        raise SystemExit(
            f"{RESULT_IN} not found.\n"
            "Run the fixed axle.py first to produce a valid (AC, in-range) "
            "optimum. Refusing to fall back to the stale config.OPTIMAL_* "
            "values: the base geometry was already shifted by them once."
        )
    with open(RESULT_IN) as f:
        opt = json.load(f)["optimum"]
    dx, dy, dtheta = opt["x"], opt["y"], opt["theta"]
    print(f"Applying shift x={dx:.3f} mm, y={dy:.3f} mm, theta={dtheta:.3f} deg, "
          f"then the largest feasible scale from {SCALE_CANDIDATES}...")

    femm.openfemm()
    try:
        # Baseline M at the optimum shift, unscaled (scale = 1.0 reference)
        femm_utils.open_scratch(OUT_FILE)
        move_coils(dx, dy, dtheta, 1.0)
        femm.mi_saveas(OUT_FILE)
        M_before = measure_M()
        femm.mi_close()
        if M_before is None:
            raise SystemExit("Even the unscaled optimum does not solve -- "
                             "re-run axle.py and inspect doe_rsm_result.json.")
        print(f"M at optimum shift, unscaled: {M_before:.6f} uH")

        M_after, scale_used = None, None
        for sf in SCALE_CANDIDATES:
            if sf == 1.0:
                M_after, scale_used = M_before, 1.0
                break
            print(f"Trying scale {sf}x ...")
            femm_utils.open_scratch(OUT_FILE)   # fresh copy each attempt
            move_coils(dx, dy, dtheta, sf)
            femm.mi_saveas(OUT_FILE)
            M = measure_M()
            femm.mi_close()
            if M is not None:
                M_after, scale_used = M, sf
                break
            print(f"   scale {sf}x collides with the rail -- trying smaller")

        print(f"Largest feasible scale: {scale_used}x -> M = {M_after:.6f} uH "
              f"(unscaled: {M_before:.6f} uH)")
        if scale_used > 1.0 and abs(M_after - M_before) < 1e-12:
            print("WARNING: M did not change despite scaling -- inspect the "
                  "output file in FEMM.")

        with open(RESULT_OUT, "w") as f:
            json.dump({
                "shift": {"x": dx, "y": dy, "theta": dtheta},
                "scale_factor": scale_used,
                "M_unscaled_uH": M_before,
                "M_scaled_uH": M_after,
                "output_fem": OUT_FILE,
            }, f, indent=2)
        print(f"Results written to {RESULT_OUT}")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Error: {e}")
    finally:
        femm.closefemm()


if __name__ == "__main__":
    main()
