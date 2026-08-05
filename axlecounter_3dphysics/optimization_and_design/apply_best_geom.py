"""
Apply the optimum geometry move plus a size scale to the coil pair, and
measure the resulting mutual inductance M.

Reads the optimum shift (x, y, theta) from reports/doe_rsm_result.json, which
axle.py produces. That JSON is the ONLY source of the optimum -- config.py
deliberately does not store one, so there is nothing stale to fall back to. If
the file is missing the script refuses to run rather than guessing.

It then tries the scale factors in SCALE_CANDIDATES largest-first and keeps
the biggest one whose scaled geometry still meshes without colliding with the
rail. Bigger coils enclose more flux, so the largest feasible scale gives the
strongest coupling.

This script NEVER writes the base .FEM. It writes:
  * femm/optimal_geom_scaled.fem     -- the moved + scaled model
  * reports/scaled_geom_result.json  -- shift, scale used, M before/after

Paths come from config (BASE_DIR / OUTPUT_DIR / FEM_FILE), not this script's
own directory, because the script lives in a subfolder.
"""
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import os

import femm

import config
from simulation_and_femm import femm_utils

# Input from axle.py, and the two artefacts this script produces.
RESULT_IN = os.path.join(config.OUTPUT_DIR, "doe_rsm_result.json")
RESULT_OUT = os.path.join(config.OUTPUT_DIR, "scaled_geom_result.json")
OUT_FILE = os.path.join(config.BASE_DIR, "femm", "optimal_geom_scaled.fem")

# Candidate coil size multipliers, tried largest-first; the first one whose
# scaled geometry still meshes (no collision with the rail) wins. 1.0 is the
# guaranteed fallback -- it means "no scaling", i.e. shift/tilt only.
SCALE_CANDIDATES = [1.5, 1.4, 1.3, 1.2, 1.1, 1.0]


def measure_M():
    """Return M in uH, or None if the geometry cannot be meshed/solved."""
    try:
        # mi_analyze(1) meshes and solves with the solver window hidden;
        # mi_loadsolution opens the field solution for post-processing.
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

    In the saved model group 1 = RX = LEFT (-x) coil and group 2 = TX =
    RIGHT (+x) coil, so the two are moved as mirror images: sx flips the
    translation direction and sth flips the rotation sense. Positive dx moves
    the coils APART. Each coil is rotated and scaled about its own midpoint,
    taken after the translation.

    IMPORTANT: FEMM clears the selection after EVERY move/rotate/scale
    operation, so the group must be re-selected before EACH operation --
    otherwise the next call acts on an empty selection and silently does
    nothing. mi_scale is issued as raw LUA with editaction 4 (= apply to the
    selected group) to work around an argument-handling bug in pyfemm.
    """
    for group, sx, sth in ((config.RX_GROUP, -1, +1), (config.TX_GROUP, +1, -1)):
        # Pre-move midpoint of this coil, used as the rotation/scale centre.
        cx0 = config.RX_CENTER_X if group == config.RX_GROUP else config.TX_CENTER_X
        cy0 = config.RX_CENTER_Y if group == config.RX_GROUP else config.TX_CENTER_Y
        femm.mi_clearselected()
        femm.mi_selectgroup(group)
        femm.mi_movetranslate(sx * dx, dy)
        # Centre follows the translation.
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
    # No DOE result means no trustworthy optimum -- stop rather than guess.
    if not os.path.exists(RESULT_IN):
        raise SystemExit(
            f"{RESULT_IN} not found.\n"
            "Run axle.py first to produce a valid (AC, in-range) optimum. "
            "There is no fallback: the optimum lives only in that JSON, so "
            "guessing one here could double-shift the geometry."
        )
    with open(RESULT_IN) as f:
        opt = json.load(f)["optimum"]
    dx, dy, dtheta = opt["x"], opt["y"], opt["theta"]
    print(f"Applying shift x={dx:.3f} mm, y={dy:.3f} mm, theta={dtheta:.3f} deg, "
          f"then the largest feasible scale from {SCALE_CANDIDATES}...")

    femm.openfemm()
    try:
        # Baseline M at the optimum shift, unscaled (scale = 1.0 reference).
        # open_scratch copies the base model to OUT_FILE and sets the AC
        # operating point, so the base .FEM is never analyzed in place.
        femm_utils.open_scratch(OUT_FILE)
        move_coils(dx, dy, dtheta, 1.0)
        femm.mi_saveas(OUT_FILE)
        M_before = measure_M()
        femm.mi_close()
        if M_before is None:
            raise SystemExit("Even the unscaled optimum does not solve -- "
                             "re-run axle.py and inspect doe_rsm_result.json.")
        print(f"M at optimum shift, unscaled: {M_before:.6f} uH")

        # Try each scale largest-first and stop at the first that solves.
        M_after, scale_used = None, None
        for sf in SCALE_CANDIDATES:
            if sf == 1.0:
                # Nothing larger fitted; the unscaled result already measured
                # above is the answer, so no extra solve is needed.
                M_after, scale_used = M_before, 1.0
                break
            print(f"Trying scale {sf}x ...")
            # Fresh copy each attempt: moves are cumulative, so a failed scale
            # must not leave its geometry behind for the next candidate.
            femm_utils.open_scratch(OUT_FILE)
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
        # Sanity check: a real scale change must move M. An unchanged value
        # means the scale operation did not reach the geometry.
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
