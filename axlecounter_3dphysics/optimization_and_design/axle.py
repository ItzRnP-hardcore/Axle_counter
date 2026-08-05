"""
DOE + response-surface (RSM) optimisation of the coil geometry.

Runs a full-factorial FEMM sweep over the DOE grid defined in config.py
(distance shift dx, height shift dy, tilt angle dtheta), measures the mutual
inductance M between the TX and RX coils at each grid point, fits a quadratic
response surface to M, and reports the geometry that maximises it.

Rules this script follows:
  * Every solve is TIME-HARMONIC at config.FREQUENCY_HZ, so eddy currents in
    the steel rail and skin effect in the copper are included.
  * All work happens on a scratch copy (temp.fem). FEMM auto-saves the open
    document when it analyzes, so solving the base .FEM in place would mutate
    it; the base model is never modified.
  * Degenerate DOE axes (an axis with only one distinct value, e.g. height)
    are excluded from the fit -- including them would make the least-squares
    matrix rank-deficient.
  * A fitted stationary point is only accepted if it is a MAXIMUM and lies
    inside the sampled range; otherwise the best sampled point is used, so the
    reported optimum is never an extrapolation outside the swept grid.
  * Grid points whose geometry cannot be meshed/solved (infeasible) are
    dropped from the fit and listed separately.

Output: reports/doe_rsm_result.json (nothing is written back to config.py).
Paths come from config (BASE_DIR / OUTPUT_DIR / FEM_FILE) rather than this
script's own directory, because the script lives in a subfolder.
"""
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import os

import femm
import numpy as np

import config
from simulation_and_femm import femm_utils

# Scratch model the DOE solves on, and the JSON report it produces.
WORK_FEM = os.path.join(config.BASE_DIR, "temp.fem")
RESULT_JSON = os.path.join(config.OUTPUT_DIR, "doe_rsm_result.json")

# Group/side mapping in the saved model (see config.py):
#   group 1 = LEFT (-x) coil  = RX = circuit "Receiver"   (open / sense coil)
#   group 2 = RIGHT (+x) coil = TX = circuit "New Circuit" (energised coil)
# Positive dx moves the coils APART (left coil -dx, right coil +dx).


def apply_geometry(dx, dy, dtheta):
    """Move both coils symmetrically on the currently open document.

    dx/dy are in mm and dtheta in degrees. The two coils are moved as mirror
    images of each other about the model centreline: the left coil goes -dx
    and rotates +dtheta about its own midpoint, the right coil goes +dx and
    rotates -dtheta.

    IMPORTANT: FEMM clears the selection after EVERY move/rotate operation, so
    the group must be re-selected before EACH call -- otherwise the following
    operation acts on an empty selection and silently does nothing (e.g. the
    tilt would never be applied and M would be identical at every angle).
    """
    # Left coil (RX, group 1): translate, then rotate about its shifted midpoint
    femm.mi_clearselected()
    femm.mi_selectgroup(config.RX_GROUP)
    femm.mi_movetranslate(-dx, dy)
    femm.mi_clearselected()
    femm.mi_selectgroup(config.RX_GROUP)
    femm.mi_moverotate(config.RX_CENTER_X - dx, config.RX_CENTER_Y + dy, dtheta)
    # Right coil (TX, group 2): same move mirrored in x and in rotation sense
    femm.mi_clearselected()
    femm.mi_selectgroup(config.TX_GROUP)
    femm.mi_movetranslate(dx, dy)
    femm.mi_clearselected()
    femm.mi_selectgroup(config.TX_GROUP)
    femm.mi_moverotate(config.TX_CENTER_X + dx, config.TX_CENTER_Y + dy, -dtheta)
    femm.mi_clearselected()


def run_experiment(dx, dy, dtheta):
    """Open a scratch copy, apply the geometry move, solve, return M in uH.

    One DOE run: fresh scratch copy of the base model, move the coils, mesh
    and solve time-harmonically, then read M from the RX flux linkage divided
    by the TX current.

    Returns None when the shifted geometry cannot be meshed/solved (e.g. the
    coil polygon collides with the rail at the extreme grid points) -- such
    points are physically infeasible and are excluded from the fit.
    """
    print(f"Running simulation: ShiftX={dx}mm, ShiftY={dy}mm, Angle={dtheta}deg...")
    femm_utils.open_scratch(WORK_FEM)          # scratch copy + AC frequency
    apply_geometry(dx, dy, dtheta)
    try:
        # mi_analyze(1) meshes and solves with the solver window hidden;
        # mi_loadsolution opens the resulting field solution for post-processing.
        femm.mi_analyze(1)
        femm.mi_loadsolution()
    except Exception as e:
        print(f"   -> INFEASIBLE at this grid point ({e}); skipping")
        femm.mi_close()
        return None
    M_uH, rx_v, rx_flux, tx_i = femm_utils.extract_mutual_inductance()
    print(f"   -> Rx Voltage: {rx_v:.4f} V | Rx Flux: {rx_flux:.4e} Wb | M: {M_uH:.4f} uH")
    femm.mo_close()
    femm.mi_close()
    return M_uH


def fit_and_optimize(runs):
    """Fit M = b0 + sum(bi*xi + bii*xi^2) over the non-degenerate axes.

    This is the response surface: a separable quadratic in each swept axis (no
    cross terms). Fitting it lets the optimum fall between grid points instead
    of being restricted to the sampled values.

    runs: list of ((dx, dy, dtheta), M_uH).
    Returns (coefficients, optimum dict, per-axis diagnostics, best sampled run).
    """
    axes = ["x", "y", "theta"]
    grids = [config.distance_shifts, config.height_shifts, config.tilt_angles]
    # Only axes actually varied in the DOE take part in the fit. A degenerate
    # axis (one distinct value) would contribute two columns that are constant
    # multiples of the intercept column, making the system rank-deficient.
    active = [i for i, g in enumerate(grids) if len(set(g)) > 1]

    # Build the design matrix: one row per feasible run, columns
    # [1, x1, x1^2, x2, x2^2, ...] for the active axes only.
    X = []
    Y = []
    for (vals, M) in runs:
        row = [1.0]
        for i in active:
            row += [vals[i], vals[i] ** 2]
        X.append(row)
        Y.append(M)
    X = np.array(X)
    Y = np.array(Y)
    # lstsq returns (coefficients, residuals, matrix rank, singular values);
    # only the coefficient vector is used here. coef[0] is the intercept, then
    # a (linear, quadratic) pair per active axis in `active` order.
    coef, _, rank, _ = np.linalg.lstsq(X, Y, rcond=None)

    # Fallback reference: the single best geometry actually measured.
    best_run = max(runs, key=lambda r: r[1])
    optimum = {"x": 0.0, "y": 0.0, "theta": 0.0}
    diag = {}
    for k, i in enumerate(active):
        b_lin = coef[1 + 2 * k]
        b_quad = coef[2 + 2 * k]
        lo, hi = min(grids[i]), max(grids[i])
        name = axes[i]
        # d/dx (b0 + b_lin*x + b_quad*x^2) = 0 at x = -b_lin/(2*b_quad).
        # A negative quadratic term means the parabola opens downward, so that
        # stationary point is a MAXIMUM -- the only case worth accepting.
        if b_quad < 0:                          # stationary point is a maximum
            stat = -b_lin / (2.0 * b_quad)
            clamped = min(max(stat, lo), hi)    # never extrapolate outside grid
            optimum[name] = clamped
            diag[name] = {"stationary": stat, "used": clamped,
                          "note": "clamped to sampled range" if stat != clamped else "interior maximum"}
        else:                                   # fit is a minimum/saddle on this axis
            # Upward-opening parabola: its stationary point is the WORST value,
            # so the fit says nothing useful; use the best measured point.
            optimum[name] = float(best_run[0][i])
            diag[name] = {"stationary": None, "used": optimum[name],
                          "note": "quadratic term non-negative; fell back to best sampled point"}
    # Fixed (degenerate) axes stay at their single grid value
    for i, g in enumerate(grids):
        if len(set(g)) == 1:
            optimum[axes[i]] = float(g[0])
            diag[axes[i]] = {"stationary": None, "used": float(g[0]), "note": "axis fixed in DOE"}
    return coef, optimum, diag, best_run


def main():
    # Full factorial: every combination of the three config grids.
    n_runs = (len(config.distance_shifts) * len(config.height_shifts)
              * len(config.tilt_angles))
    print(f"Starting Automated RSM Optimization ({n_runs} full-factorial runs, "
          f"{config.FREQUENCY_HZ / 1e3:.0f} kHz time-harmonic)...")
    femm.openfemm()
    try:
        runs = []          # ((dx, dy, dtheta), M_uH) for every solved point
        infeasible = []    # grid points that would not mesh/solve
        for dx in config.distance_shifts:
            for dy in config.height_shifts:
                for dtheta in config.tilt_angles:
                    M = run_experiment(dx, dy, dtheta)
                    if M is None:
                        infeasible.append((dx, dy, dtheta))
                    else:
                        runs.append(((dx, dy, dtheta), M))
        if infeasible:
            print(f"\n{len(infeasible)} infeasible grid point(s) excluded "
                  f"(geometry collision): {infeasible}")
        # The quadratic surface needs more points than it has coefficients;
        # too few feasible runs means the fit would be meaningless.
        if len(runs) < 7:
            raise RuntimeError(f"only {len(runs)} feasible runs -- too few to fit "
                               "the response surface; shrink the DOE grid in config.py")

        print("\n--- Solving Response Surface Matrix ---")
        coef, optimum, diag, best_run = fit_and_optimize(runs)

        print("\n=== OPTIMAL CONFIGURATION (within sampled range) ===")
        for name in ("x", "y", "theta"):
            print(f"  {name:6}: {optimum[name]:8.3f}   ({diag[name]['note']})")
        print(f"  Best sampled run: {best_run[0]} -> {best_run[1]:.4f} uH")

        # The fitted optimum generally sits between grid points, so it has not
        # been simulated yet. Solve it for real to confirm it is both feasible
        # and as good as the surface predicts.
        print("\nVerifying optimum with a live FEMM solve...")
        M_opt = run_experiment(optimum["x"], optimum["y"], optimum["theta"])
        if M_opt is None:
            print("Fitted optimum is infeasible -- falling back to best sampled point.")
            rejected = dict(optimum)
            optimum = dict(zip(("x", "y", "theta"), (float(v) for v in best_run[0])))
            M_opt = best_run[1]
            # Keep the diagnostics in sync with the optimum actually reported.
            # Without this the JSON would contradict itself: `optimum` holds
            # the fallback point while `diagnostics[*]["used"]` still describes
            # the rejected fitted point. The rejected value is retained under
            # "rejected_fit_value" so the fit remains traceable.
            for name in ("x", "y", "theta"):
                if diag[name]["used"] != optimum[name]:
                    diag[name] = {
                        "stationary": diag[name].get("stationary"),
                        "used": optimum[name],
                        "rejected_fit_value": rejected[name],
                        "note": diag[name]["note"] +
                                "; fitted point was INFEASIBLE (mesh/solve failed), "
                                "superseded by the best sampled run",
                    }
        print(f"Optimal Mutual Inductance extracted: {M_opt:.4f} uH")

        # Full record: the chosen geometry, the raw sweep, the excluded points
        # and the fit coefficients, so the result can be audited later.
        with open(RESULT_JSON, "w") as f:
            json.dump({
                "frequency_hz": config.FREQUENCY_HZ,
                "optimum": optimum,
                "optimum_M_uH": M_opt,
                "best_sampled": {"shift": best_run[0], "M_uH": best_run[1]},
                "infeasible_points": infeasible,
                "diagnostics": diag,
                "coefficients": list(coef),
                "runs": [{"shift": s, "M_uH": m} for s, m in runs],
            }, f, indent=2)
        print(f"Done! Results saved to {RESULT_JSON}")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"An error occurred: {e}")
    finally:
        femm.closefemm()


if __name__ == "__main__":
    main()
