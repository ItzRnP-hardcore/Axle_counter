"""
Live FEMM validation run.
Opens the base geometry and solves it TWICE:
  (1) magnetostatic  (Frequency = 0)  -- as the file ships today
  (2) time-harmonic  (Frequency = 20 kHz) -- the physically correct AC mode
Extracts mutual inductance from each and writes a comparison to
reports/femm_live_result.txt so the difference is visible.

Run by double-clicking run_femm.bat (which handles pyfemm install + logging).
"""
import os, sys, traceback

HERE = os.path.dirname(os.path.abspath(__file__))
OUT  = os.path.join(HERE, "reports", "femm_live_result.txt")
os.makedirs(os.path.dirname(OUT), exist_ok=True)

def log(msg, f):
    print(msg); f.write(msg + "\n"); f.flush()

def solve_at(femm, freq, fem_file):
    femm.opendocument(fem_file)
    # first arg of mi_probdef is the frequency -> switches solver mode
    femm.mi_probdef(freq, "millimeters", "planar", 1e-8, 1, 30, 0)
    femm.mi_saveas(os.path.join(HERE, "_live_tmp.fem"))
    femm.mi_analyze(1)
    femm.mi_loadsolution()
    rx = femm.mo_getcircuitproperties("Receiver")     # [I, V, flux]
    tx = femm.mo_getcircuitproperties("New Circuit")
    rx_v = abs(rx[1]); rx_flux = abs(rx[2]); tx_i = abs(tx[0])
    M_uH = (rx_flux / tx_i) * 1e6 if tx_i > 0 else 0.0
    femm.mo_close(); femm.mi_close()
    return M_uH, rx_v, rx_flux, tx_i

with open(OUT, "w") as f:
    log("=== FEMM LIVE RUN ===", f)
    try:
        try:
            import femm
        except ImportError:
            log("pyfemm not found -> installing...", f)
            import subprocess
            subprocess.run([sys.executable, "-m", "pip", "install", "pyfemm"], check=True)
            import femm
        fem_file = os.path.join(HERE, "femm", "InternMadebyPratham.FEM")
        log(f"FEM file: {fem_file}", f)
        femm.openfemm()
        for label, freq in [("MAGNETOSTATIC (f=0)", 0), ("TIME-HARMONIC (f=20kHz)", 20000)]:
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
