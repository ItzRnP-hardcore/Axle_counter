"""
FEMM parameter sweep -- property-based DOE (robust rewrite).

WHY THE REWRITE
---------------
The previous version (a) scaled coil GEOMETRY with mi_scale, which distorted
coil-vs-rail alignment and gave noisy, non-monotonic "area" results, and
(b) analysed the BASE .FEM file in place -- and because FEMM auto-saves a
document when it analyses, that quietly overwrote the user's base geometry.

This version fixes both:
  * It immediately saves a SCRATCH working copy (_sweep_work.fem) and does all
    work there, so the base model is never modified.
  * It varies the coil ONLY through block/circuit PROPERTIES -- number of turns
    (a block property) and drive current (a circuit property) -- never geometry.
    (Coil AREA is inherently geometric and cannot be a block property, so it is
    intentionally not swept here; use a dedicated geometry study for that.)

Runs at the AC operating point from config.FREQUENCY_HZ.
"""
import femm
import csv
import os
import config

CSV_OUT = os.path.join(config.OUTPUT_DIR, "coil_parameter_sweep_femm.csv")
WORK_FEM = os.path.join(config.BASE_DIR, "_sweep_work.fem")

# DOE dimensions -- both are pure properties, no geometry involved
turns_sweep   = [50, 100, 150, 200]
current_sweep = [2.5, 5.0]      # Amperes in the energised ("New Circuit") coil

# Coil half-labels for the CURRENT base geometry: (x, y, circuit, group, sign)
# Two halves per coil get +turns / -turns so each coil stays balanced.
COIL_HALVES = [
    (48.09, 110.3,   "New Circuit", 2, +1),   # energised coil, half A
    (70.29, 107.29,  "New Circuit", 2, -1),   # energised coil, half B
    (-72.71, 121.26, "Receiver",    1, +1),   # sense coil, half A
    (-50.59, 124.0,  "Receiver",    1, -1),   # sense coil, half B
]
COIL_MATERIAL = "18 AWG"

def run_sweep():
    print("Starting property-based FEMM sweep (no geometry scaling)...")
    femm.openfemm()
    results = []
    try:
        for turns in turns_sweep:
            for cur in current_sweep:
                print(f"Testing Turns={turns}, Drive={cur} A ...")
                femm.opendocument(config.FEM_FILE)
                # Work on a scratch copy so the base model is NEVER overwritten
                femm.mi_saveas(WORK_FEM)
                # AC operating point
                femm.mi_probdef(config.FREQUENCY_HZ, "millimeters", "planar", 1e-8, 1, 30, 0)
                # Set turns on each coil half (block property) -- balanced +/- per coil
                for (x, y, circuit, group, sign) in COIL_HALVES:
                    femm.mi_selectlabel(x, y)
                    femm.mi_setblockprop(COIL_MATERIAL, 1, 0, circuit, 0, group, sign * turns)
                    femm.mi_clearselected()
                # Set drive current on the energised circuit (circuit property)
                femm.mi_modifycircprop("New Circuit", 1, cur)
                # Solve
                femm.mi_analyze(1)
                femm.mi_loadsolution()
                rx = femm.mo_getcircuitproperties("Receiver")
                tx = femm.mo_getcircuitproperties("New Circuit")
                rx_v = abs(rx[1]); rx_flux = abs(rx[2]); tx_i = abs(tx[0])
                M_uH = (rx_flux / tx_i) * 1e6 if tx_i > 0 else 0.0
                results.append([turns, cur, tx_i, rx_flux, M_uH, rx_v])
                femm.mo_close(); femm.mi_close()
    except Exception as e:
        print(f"Error during sweep: {e}")
        import traceback; traceback.print_exc()
    finally:
        femm.closefemm()

    with open(CSV_OUT, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Turns", "Drive_Current_A", "TX_Current_A", "RX_Flux_Wb",
                    "Mutual_Inductance_uH", "RX_Voltage_V"])
        w.writerows(results)
    print(f"Sweep complete ({len(results)} runs). Data -> {CSV_OUT}")

if __name__ == "__main__":
    run_sweep()
