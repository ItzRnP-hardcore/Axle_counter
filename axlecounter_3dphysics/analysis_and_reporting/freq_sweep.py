"""Frequency sweep of the FEMM coil model from 10 kHz to 20 kHz.

For each frequency the shipped .FEM model is re-solved time-harmonically and
the TX/RX circuit results are recorded:
  * mutual inductance   M   = RX flux linkage / TX current
  * TX self-inductance  L   = TX flux linkage / TX current
  * RX open-circuit induced voltage

Writes reports/frequency_sweep_femm.csv (one row per frequency). Requires
pyfemm and a working FEMM installation.
"""
import sys, os

# Paths come from config (BASE_DIR / OUTPUT_DIR / FEM_FILE), not from this
# script's own directory -- the script lives in a subfolder of the project.
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import femm
import csv
import os
import config

# Every solve is done on a scratch copy (WORK_FEM) so the shipped .FEM model
# is never modified by the sweep.
CSV_OUT = os.path.join(config.OUTPUT_DIR, "frequency_sweep_femm.csv")
WORK_FEM = os.path.join(config.BASE_DIR, "_freq_sweep_work.fem")

# 10.0, 10.5, ... 20.0 kHz -- 21 points in 500 Hz steps.
frequencies = [10000 + i * 500 for i in range(21)]

def run_freq_sweep():
    print(f"Starting frequency sweep from 10kHz to 20kHz... (Total {len(frequencies)} points)")
    femm.openfemm()
    results = []
    try:
        for freq in frequencies:
            print(f"Testing Frequency={freq} Hz ...")
            femm.opendocument(config.FEM_FILE)
            femm.mi_saveas(WORK_FEM)
            
            # Re-declare the problem at the new frequency. The depth is the
            # real coil axial length, so the 2D planar solution carries
            # absolute physical units (Wb, V, H) rather than per-metre ones.
            femm.mi_probdef(freq, "millimeters", "planar", 1e-8,
                            config.COIL_DEPTH_MM, 30, 0)
            
            # Mesh + solve, then load the solution so the post-processor
            # (mo_*) calls below can read circuit results back out.
            femm.mi_analyze(1)
            femm.mi_loadsolution()
            
            # mo_getcircuitproperties returns (current, voltage, flux linkage)
            # for a named circuit.
            rx = femm.mo_getcircuitproperties(config.RX_CIRCUIT)
            tx = femm.mo_getcircuitproperties(config.TX_CIRCUIT)
            
            rx_v = abs(rx[1])
            rx_flux = abs(rx[2])
            tx_i = abs(tx[0])
            
            # Mutual inductance: flux linked into the RX coil per amp of TX
            # current. The RX coil carries no current, so this is pure
            # coupling. rx_v is then the open-circuit induced voltage, which
            # by Faraday's law should equal omega * rx_flux.
            M_uH = (rx_flux / tx_i) * 1e6 if tx_i > 0 else 0.0
            
            # TX self-inductance: its own flux linkage per amp of its own
            # current. The two coils are near-symmetric, so L_RX is similar.
            tx_flux = abs(tx[2])
            L_tx_uH = (tx_flux / tx_i) * 1e6 if tx_i > 0 else 0.0
            
            results.append([freq, tx_i, rx_flux, M_uH, rx_v, L_tx_uH])
            
            femm.mo_close()
            femm.mi_close()
    except Exception as e:
        print(f"Error during frequency sweep: {e}")
        import traceback; traceback.print_exc()
    finally:
        femm.closefemm()

    # A failed sweep must not clobber a good CSV from a previous run.
    if not results:
        print("No results collected -- keeping the previous CSV untouched.")
        return
    with open(CSV_OUT, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Frequency_Hz", "TX_Current_A", "RX_Flux_Wb", "Mutual_Inductance_uH", "RX_Voltage_V", "L_TX_uH"])
        w.writerows(results)
    print(f"Sweep complete ({len(results)} runs). Data -> {CSV_OUT}")

if __name__ == "__main__":
    run_freq_sweep()
