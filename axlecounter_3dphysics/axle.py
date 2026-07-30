"""
DOE + response-surface (RSM) optimisation of the coil geometry.

Runs a full-factorial sweep over (distance shift, height shift, tilt angle),
fits a quadratic response surface to the mutual inductance, and reports the
optimum. Fixes over the original version:
  * Solves TIME-HARMONIC at config.FREQUENCY_HZ (the old run was DC).
  * Works on a scratch copy -- the base .FEM is never modified.
  * Degenerate DOE axes (e.g. height fixed at 0) are excluded from the fit
    instead of producing a rank-deficient matrix.
  * The stationary point is only accepted if it is a MAXIMUM and lies inside
    the sampled range; otherwise the best sampled point is used. No more
    extrapolated "optima" outside the swept grid.
  * Results are written to reports/doe_rsm_result.json, not appended to
    config.py.
"""
import json
import os

import femm
import numpy as np

import config
import femm_utils

WORK_FEM = os.path.join(config.BASE_DIR, "temp.fem")
RESULT_JSON = os.path.join(config.OUTPUT_DIR, "doe_rsm_result.json")

# Group/side mapping for the CURRENT base file (see config.py):
#   group 1 = LEFT coil  = RX ("Receiver")
#   group 2 = RIGHT coil = TX ("New Circuit")
# Positive dx moves the coils APART (left coil -dx, right coil +dx).


def apply_geometry(dx, dy, dtheta):
    """Move both coils symmetrically on the currently open document.

    NOTE: FEMM clears the selection after mi_movetranslate, so the group must
    be re-selected before mi_moverotate -- otherwise the rotation silently
    does nothing (which is exactly what happened in every earlier DOE run:
    M was bit-identical across all tilt angles).
    """
    # Left coil (RX, group 1)
    femm.mi_clearselected()
    femm.mi_selectgroup(config.RX_GROUP)
    femm.mi_movetranslate(-dx, dy)
    femm.mi_clearselected()
    femm.mi_selectgroup(config.RX_GROUP)
    femm.mi_moverotate(config.RX_CENTER_X - dx, config.RX_CENTER_Y + dy, dtheta)
    # Right coil (TX, group 2), mirrored
    femm.mi_clearselected()
    femm.mi_selectgroup(config.TX_GROUP)
    femm.mi_movetranslate(dx, dy)
    femm.mi_clearselected()
    femm.mi_selectgroup(config.TX_GROUP)
    femm.mi_moverotate(config.TX_CENTER_X + dx, config.TX_CENTER_Y + dy, -dtheta)
    femm.mi_clearselected()


def run_experiment(dx, dy, dtheta):
    """Open a scratch copy, apply the geometry move, solve, return M in uH.

    Returns None when the shifted geometry cannot be meshed/solved (e.g. the
    coil polygon collides with the rail at the extreme grid points) -- such
    points are physically infeasible and are excluded from the fit.
    """
    print(f"Running simulation: ShiftX={dx}mm, ShiftY={dy}mm, Angle={dtheta}deg...")
    femm_utils.open_scratch(WORK_FEM)          # scratch copy + AC frequency
    apply_geometry(dx, dy, dtheta)
    try:
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

    runs: list of ((dx, dy, dtheta), M_uH).
    Returns (optimum dict, per-axis diagnostics).
    """
    axes = ["x", "y", "theta"]
    grids = [config.distance_shifts, config.height_shifts, config.tilt_angles]
    active = [i for i, g in enumerate(grids) if len(set(g)) > 1]

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
    coef, _, rank, _ = np.linalg.lstsq(X, Y, rcond=None)

    best_run = max(runs, key=lambda r: r[1])
    optimum = {"x": 0.0, "y": 0.0, "theta": 0.0}
    diag = {}
    for k, i in enumerate(active):
        b_lin = coef[1 + 2 * k]
        b_quad = coef[2 + 2 * k]
        lo, hi = min(grids[i]), max(grids[i])
        name = axes[i]
        if b_quad < 0:                          # stationary point is a maximum
            stat = -b_lin / (2.0 * b_quad)
            clamped = min(max(stat, lo), hi)    # never extrapolate outside grid
            optimum[name] = clamped
            diag[name] = {"stationary": stat, "used": clamped,
                          "note": "clamped to sampled range" if stat != clamped else "interior maximum"}
        else:                                   # fit is a minimum/saddle on this axis
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
    n_runs = (len(config.distance_shifts) * len(config.height_shifts)
              * len(config.tilt_angles))
    print(f"Starting Automated RSM Optimization ({n_runs} full-factorial runs, "
          f"{config.FREQUENCY_HZ / 1e3:.0f} kHz time-harmonic)...")
    femm.openfemm()
    try:
        runs = []
        infeasible = []
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
        if len(runs) < 7:
            raise RuntimeError(f"only {len(runs)} feasible runs -- too few to fit "
                               "the response surface; shrink the DOE grid in config.py")

        print("\n--- Solving Response Surface Matrix ---")
        coef, optimum, diag, best_run = fit_and_optimize(runs)

        print("\n=== OPTIMAL CONFIGURATION (within sampled range) ===")
        for name in ("x", "y", "theta"):
            print(f"  {name:6}: {optimum[name]:8.3f}   ({diag[name]['note']})")
        print(f"  Best sampled run: {best_run[0]} -> {best_run[1]:.4f} uH")

        # Verify the fitted optimum with a live solve
        print("\nVerifying optimum with a live FEMM solve...")
        M_opt = run_experiment(optimum["x"], optimum["y"], optimum["theta"])
        if M_opt is None:
            print("Fitted optimum is infeasible -- falling back to best sampled point.")
            optimum = dict(zip(("x", "y", "theta"), (float(v) for v in best_run[0])))
            M_opt = best_run[1]
        print(f"Optimal Mutual Inductance extracted: {M_opt:.4f} uH")

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
