"""
Live FEMM validation run.

Solves the base geometry TWICE and compares the two operating points:
  (1) magnetostatic  (Frequency = 0)
  (2) time-harmonic  (Frequency = config.FREQUENCY_HZ, 20 kHz) -- the
      physically correct AC mode for an axle counter
For each solve it reports TX current, RX flux linkage, RX induced voltage and
the mutual inductance M.

Writes (and echoes to stdout) reports/femm_live_result.txt. Installs pyfemm
on the fly if it is missing.

Run with `py -3 simulation_and_femm/femm_run_once.py` (or run_femm.bat, which
handles the pyfemm install + logging).
"""
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import os, sys, traceback

import config

# Paths come from config, NOT from this file's own directory: the scripts live
# in subfolders, so dirname(__file__) is not the project root.
OUT = os.path.join(config.OUTPUT_DIR, "femm_live_result.txt")

def log(msg, f):
    """Print a line and mirror it into the open report file."""
    print(msg); f.write(msg + "\n"); f.flush()

def solve_at(femm, freq, fem_file):
    """Solve `fem_file` at excitation frequency `freq` (Hz).

    Returns (M_uH, rx_voltage, rx_flux, tx_current).
    """
    femm.opendocument(fem_file)
    # mi_probdef(frequency, units, type, precision, depth, minangle, acsolver).
    # The first argument is the frequency and it selects the solver mode:
    # 0 = magnetostatic, > 0 = time-harmonic. Depth must be the real coil
    # axial length so absolute flux/M/voltage are physical, not per-mm, and
    # comes from config. The precision (1e-8), minimum mesh angle (30) and
    # acsolver (0) are FEMM numerical settings, not physical parameters, so
    # they stay local.
    femm.mi_probdef(freq, "millimeters", "planar", 1e-8,
                    config.COIL_DEPTH_MM, 30, 0)
    # Redirect the document to a scratch file BEFORE analyzing: FEMM auto-saves
    # the open document on analyze, which would otherwise rewrite the base FEM.
    femm.mi_saveas(os.path.join(config.BASE_DIR, "_live_tmp.fem"))
    femm.mi_analyze(1)      # mesh + solve (1 = run minimised, no solver window)
    femm.mi_loadsolution()  # open the result so the mo_* post-processor works
    # mo_getcircuitproperties -> [current, voltage, flux_linkage] for a circuit.
    # TX = "New Circuit" = group 2 = right (+x) coil, the energised one.
    # RX = "Receiver"    = group 1 = left (-x) coil, the open sense winding.
    rx = femm.mo_getcircuitproperties(config.RX_CIRCUIT)   # [I, V, flux]
    tx = femm.mo_getcircuitproperties(config.TX_CIRCUIT)
    rx_v = abs(rx[1]); rx_flux = abs(rx[2]); tx_i = abs(tx[0])
    # M = RX flux linkage per amp of TX current, converted to microhenries.
    M_uH = (rx_flux / tx_i) * 1e6 if tx_i > 0 else 0.0
    femm.mo_close(); femm.mi_close()   # close post-processor, then the model
    return M_uH, rx_v, rx_flux, tx_i

with open(OUT, "w") as f:
    log("=== FEMM LIVE RUN ===", f)
    try:
        try:
            import femm
        except ImportError:
            # pyfemm is the Python bridge to the FEMM application; pull it in
            # on demand so a fresh machine can run this script unattended.
            log("pyfemm not found -> installing...", f)
            import subprocess
            subprocess.run([sys.executable, "-m", "pip", "install", "pyfemm"], check=True)
            import femm
        fem_file = config.FEM_FILE
        log(f"FEM file: {fem_file}", f)
        femm.openfemm()   # launch the FEMM GUI process this script drives
        ac_label = f"TIME-HARMONIC (f={config.FREQUENCY_HZ/1e3:.0f}kHz)"
        # Same geometry, two operating points -- the DC case is the reference,
        # the AC case is the one that matches real axle-counter operation.
        # The f = 0 below is the solver's magnetostatic mode selector, not a
        # physical operating point, so it stays local; the AC point is
        # config.FREQUENCY_HZ.
        for label, freq in [("MAGNETOSTATIC (f=0)", 0),
                            (ac_label, config.FREQUENCY_HZ)]:
            M, v, flux, i = solve_at(femm, freq, fem_file)
            log(f"\n[{label}]", f)
            log(f"  TX current        : {i:.4f} A", f)
            log(f"  RX flux linkage   : {flux:.4e} Wb", f)
            log(f"  RX induced voltage: {v:.6f} V", f)
            log(f"  Mutual inductance : {M:.6f} uH", f)
        femm.closefemm()
        log("\nDONE OK", f)
    except Exception as e:
        log("ERROR: " + str(e), f)
        f.write(traceback.format_exc())
