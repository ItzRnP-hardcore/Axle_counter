"""
Run the whole Axle Counter study end to end, in dependency order.

This is the single entry point for the project. It executes every FEMM solve,
every analytic model, both notebooks and every figure generator, then finishes
with the physics sanity suite as a pass/fail gate.

WHY THE ORDER MATTERS
---------------------
The stages are not independent -- several consume files that an earlier stage
writes:

  femm_run_once   -> _live_tmp.fem/.ans     : the matched, freshly-solved base
                                              geometry that make_figs prefers
                                              for figures 01/02
  femm_sweep      -> coil_parameter_sweep_femm.csv
                                            : the 100-turn row of this CSV is
                                              the anchor sanity_check compares
                                              config.M0_UH against
  femm_wheel_dip  -> _wheel_work.fem/.ans   : the solved wheel-present model
                                              that generate_wheel_figure draws
  axle            -> doe_rsm_result.json    : apply_best_geom REFUSES to run
                                              without it
  notebooks       -> axle_counter_sweep_data.csv
                                            : figures 05-09 are built from it

So: live solves first, then analytics, then notebooks, then figures, then the
sanity gate last (it audits everything the earlier stages produced).

FEMM RUNS SEQUENTIALLY
----------------------
FEMM is a single-instance desktop application driven through pyfemm. Two solver
stages must never run at the same time or they fight over the same session, so
every stage here is run one after another -- never in parallel.

USAGE
-----
    py -3 run_all.py                 # everything (default)
    py -3 run_all.py --list          # print the plan, run nothing
    py -3 run_all.py --skip-femm     # analytics/figures only, no solver
    py -3 run_all.py --skip-notebooks
    py -3 run_all.py --with-optional # also run the print-only helper scripts
    py -3 run_all.py --with-debug    # also run the FEMM debug probes
    py -3 run_all.py --continue-on-error

Exit code is 0 only if every stage that ran succeeded (and the sanity suite
reported no failures).
"""
import argparse
import os
import subprocess
import sys
import time

# Project root = the folder holding this file. Every stage path below is
# relative to it, so the runner works no matter where it is invoked from.
ROOT = os.path.dirname(os.path.abspath(__file__))


class Stage:
    """One unit of work in the pipeline.

    kind   -- "script" (run with the Python interpreter) or "notebook"
              (executed in place with nbclient, refreshing its stored outputs)
    femm   -- True if the stage drives the FEMM solver; these are the slow
              stages and the ones skipped by --skip-femm
    group  -- one of the optional buckets: None (always run), "optional"
              (print-only helpers) or "debug" (FEMM probes)
    """

    def __init__(self, path, note, kind="script", femm=False, group=None):
        self.path = path
        self.note = note
        self.kind = kind
        self.femm = femm
        self.group = group

    @property
    def name(self):
        return os.path.basename(self.path)


# ---------------------------------------------------------------------------
# The pipeline. Order is deliberate -- see the docstring above.
# ---------------------------------------------------------------------------
STAGES = [
    # -- 1. Live FEMM solves -------------------------------------------------
    Stage("simulation_and_femm/femm_run_once.py",
          "base model solved magnetostatic + time-harmonic; writes "
          "femm_live_result.txt and the _live_tmp.* pair used by figures 01/02",
          femm=True),
    Stage("simulation_and_femm/femm_sweep.py",
          "8 solves: turns x drive current; writes coil_parameter_sweep_femm.csv "
          "(the M0 anchor)",
          femm=True),
    Stage("analysis_and_reporting/freq_sweep.py",
          "21 solves across 10-20 kHz; writes frequency_sweep_femm.csv",
          femm=True),
    Stage("simulation_and_femm/femm_wheel_dip.py",
          "2 solves with/without the steel wheel; writes wheel_dip.json and the "
          "_wheel_work.* pair used by figure 11",
          femm=True),
    Stage("optimization_and_design/axle.py",
          "full-factorial DOE + response surface (35 solves); writes "
          "doe_rsm_result.json",
          femm=True),
    Stage("optimization_and_design/apply_best_geom.py",
          "applies the DOE optimum + largest feasible scale; writes "
          "scaled_geom_result.json and femm/optimal_geom_scaled.fem",
          femm=True),

    # -- 2. Analytic models (no solver) --------------------------------------
    Stage("analysis_and_reporting/generate_data_points.py",
          "analytic turns/area sweep anchored to config.M0_UH; writes "
          "coil_parameter_sweep.csv"),
    Stage("optimization_and_design/optimize_air_core.py",
          "air-core design table across capacitor voltage classes; writes "
          "optimal_design.json"),

    # -- 3. Notebooks --------------------------------------------------------
    # sweep_analysis.ipynb writes axle_counter_sweep_data.csv, which figures
    # 05-09 are built from, so both notebooks run before make_figs.
    Stage("analysis_and_reporting/physics_calculation.ipynb",
          "FEMM-anchored operating point; writes the sine/square comparison PNGs",
          kind="notebook"),
    Stage("analysis_and_reporting/sweep_analysis.ipynb",
          "legacy flux-loss sweep; writes axle_counter_sweep_data.csv and the "
          "sweep_*.png figures",
          kind="notebook"),

    # -- 4. Figures ----------------------------------------------------------
    Stage("analysis_and_reporting/make_figs.py",
          "figures 01-09 (flux map, geometry, analytic grids, legacy sweep)"),
    Stage("analysis_and_reporting/generate_wheel_figure.py",
          "figure 11 (flux map with the wheel present)"),

    # -- 5. Validation gate --------------------------------------------------
    # Runs last: it audits every CSV/JSON the stages above produced and exits
    # non-zero if any physics identity fails.
    Stage("analysis_and_reporting/sanity_check.py",
          "physics sanity suite over every report; writes sanity_check_report.md"),

    # -- Optional: print-only helpers, no files written ----------------------
    Stage("analysis_and_reporting/summary.py",
          "prints the scaled operating-point summary", group="optional"),
    Stage("optimization_and_design/calc_caps.py",
          "prints resonant capacitor / voltage ratings for 3 coil scenarios",
          group="optional"),
    Stage("optimization_and_design/optimize_coils.py",
          "slow analytic grid search for maximum secondary voltage",
          group="optional"),

    # -- Debug: FEMM probes, not part of the results pipeline ----------------
    Stage("simulation_and_femm/test_move.py",
          "probe: confirms block labels re-assign and groups move without "
          "breaking the mesh",
          femm=True, group="debug"),
    Stage("optimization_and_design/check_area.py",
          "probe: prints the cross-section area of one TX coil half",
          femm=True, group="debug"),
]


def run_script(path):
    """Execute a .py stage in a subprocess. Returns its exit code.

    Run from ROOT with ROOT on PYTHONPATH so `import config` resolves the same
    way it does when a script is launched directly.
    """
    env = dict(os.environ)
    env["PYTHONPATH"] = ROOT + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run([sys.executable, os.path.join(ROOT, path)],
                          cwd=ROOT, env=env).returncode


def run_notebook(path):
    """Execute a notebook in place, refreshing its stored outputs.

    Returns 0 on success, 1 on failure, and 2 if nbclient/nbformat are missing
    (treated as a skip rather than a hard error).
    """
    try:
        import nbformat
        from nbclient import NotebookClient
    except ImportError:
        print("   nbclient/nbformat not installed -- skipping this notebook "
              "(pip install nbclient nbformat)")
        return 2
    full = os.path.join(ROOT, path)
    nb = nbformat.read(full, as_version=4)
    # Execute with the notebook's own folder as CWD, matching how a user would
    # open it in Jupyter. The notebooks locate config.py by walking upward.
    client = NotebookClient(nb, timeout=1800, kernel_name="python3",
                            resources={"metadata": {"path": os.path.dirname(full)}})
    try:
        client.execute()
        nbformat.write(nb, full)
        return 0
    except Exception as exc:
        print(f"   notebook failed: {type(exc).__name__}: {exc}")
        return 1


def main():
    ap = argparse.ArgumentParser(
        description="Run the full Axle Counter FEMM + analytic pipeline.")
    ap.add_argument("--list", action="store_true",
                    help="print the execution plan and exit")
    ap.add_argument("--skip-femm", action="store_true",
                    help="skip every stage that drives the FEMM solver")
    ap.add_argument("--skip-notebooks", action="store_true",
                    help="skip the two Jupyter notebooks")
    ap.add_argument("--with-optional", action="store_true",
                    help="also run the print-only helper scripts")
    ap.add_argument("--with-debug", action="store_true",
                    help="also run the FEMM debug probes")
    ap.add_argument("--continue-on-error", action="store_true",
                    help="keep going after a stage fails instead of stopping")
    args = ap.parse_args()

    # Build the list of stages to actually run, applying the filters.
    plan = []
    for st in STAGES:
        if st.group == "optional" and not args.with_optional:
            continue
        if st.group == "debug" and not args.with_debug:
            continue
        if st.femm and args.skip_femm:
            continue
        if st.kind == "notebook" and args.skip_notebooks:
            continue
        plan.append(st)

    print("=" * 78)
    print("AXLE COUNTER -- FULL PIPELINE")
    print(f"Project root : {ROOT}")
    print(f"Interpreter  : {sys.executable}")
    print(f"Stages       : {len(plan)}")
    print("=" * 78)
    for i, st in enumerate(plan, 1):
        tag = "FEMM" if st.femm else ("NB" if st.kind == "notebook" else "    ")
        print(f"{i:2}. [{tag:4}] {st.path}")
        print(f"           {st.note}")
    print("=" * 78)

    if args.list:
        print("--list given: nothing was executed.")
        return 0

    if not args.skip_femm:
        print("NOTE: FEMM stages run sequentially and will open the FEMM window\n"
              "      repeatedly. Do not use FEMM interactively until this finishes.\n")

    results = []          # (stage, status, seconds)
    t_all = time.time()
    for i, st in enumerate(plan, 1):
        print("\n" + "-" * 78)
        print(f"[{i}/{len(plan)}] {st.path}")
        print(f"        {st.note}")
        print("-" * 78)
        t0 = time.time()
        try:
            rc = run_notebook(st.path) if st.kind == "notebook" else run_script(st.path)
        except KeyboardInterrupt:
            print("\nInterrupted by user.")
            return 130
        except Exception as exc:                      # runner-level failure
            print(f"   runner error: {type(exc).__name__}: {exc}")
            rc = 1
        dt = time.time() - t0
        status = {0: "OK", 2: "SKIP"}.get(rc, "FAIL")
        results.append((st, status, dt))
        print(f"   -> {status} in {dt:.1f}s")
        if status == "FAIL" and not args.continue_on_error:
            print("\nStopping (use --continue-on-error to push through).")
            break

    # ---- summary ----------------------------------------------------------
    print("\n" + "=" * 78)
    print("SUMMARY")
    print("=" * 78)
    for st, status, dt in results:
        print(f"  {status:4}  {dt:7.1f}s  {st.path}")
    n_fail = sum(1 for _, s, _ in results if s == "FAIL")
    n_skip = sum(1 for _, s, _ in results if s == "SKIP")
    n_ok = sum(1 for _, s, _ in results if s == "OK")
    print("-" * 78)
    print(f"  {n_ok} ok, {n_fail} failed, {n_skip} skipped, "
          f"{len(plan) - len(results)} not reached "
          f"-- total {time.time() - t_all:.1f}s")
    print(f"  Reports: {os.path.join(ROOT, 'reports')}")
    print("=" * 78)
    # Non-zero exit if anything failed, so CI / a batch file can detect it.
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
