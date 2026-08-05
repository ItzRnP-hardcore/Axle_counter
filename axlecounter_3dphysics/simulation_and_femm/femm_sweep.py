"""
FEMM parameter sweep -- property-based design of experiments.

Sweeps the coil across a grid of turns x drive current, solving each
combination at the AC operating point (config.FREQUENCY_HZ) and recording the
resulting TX current, RX flux linkage, mutual inductance and RX voltage.

Two ground rules:
  * All work happens on a SCRATCH copy (_sweep_work.fem). FEMM auto-saves the
    open document when it analyzes, so solving the base .FEM directly would
    silently overwrite the user's model.
  * Only block/circuit PROPERTIES are varied -- turns (a block property) and
    drive current (a circuit property). Geometry is never touched. Coil AREA
    is geometric and cannot be expressed as a block property, which is why it
    is not part of this sweep; it needs a dedicated geometry study.

Writes reports/coil_parameter_sweep_femm.csv (one row per combination). If no
run succeeds, the existing CSV is left untouched.
"""
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import femm
import csv
import os
import config

# Output paths come from config, NOT from this file's directory: the scripts
# live in subfolders, so dirname(__file__) is not the project root.
CSV_OUT = os.path.join(config.OUTPUT_DIR, "coil_parameter_sweep_femm.csv")
WORK_FEM = os.path.join(config.BASE_DIR, "_sweep_work.fem")

# DOE dimensions -- both are pure properties, no geometry involved.
# Both grids come from config so this sweep, the analytic sweeps and
# sanity_check.py describe the same experiment. config.TURNS_SWEEP contains
# config.BASELINE_TURNS, which is the row sanity_check.py validates M0_UH
# against; config.CURRENT_SWEEP is in Amperes in the energised
# ("New Circuit") coil.
turns_sweep   = config.TURNS_SWEEP
current_sweep = config.CURRENT_SWEEP

# Flattened list of the four coil block labels, as
# (x, y, circuit_name, femm_group, sign). A FEMM "group" is an integer tag
# attached to geometry so a whole coil can be selected in one call. In the
# saved model the energised circuit "New Circuit" is the RIGHT (+x) coil,
# group 2; the open sense circuit "Receiver" is the LEFT (-x) coil, group 1.
# The sign carries the go/return direction of each coil half, so the two
# halves of one coil get +turns and -turns and the winding stays balanced.
COIL_HALVES = (
    [(x, y, config.TX_CIRCUIT, config.TX_GROUP, 1 if t > 0 else -1)
     for (x, y, t) in config.TX_LABELS]
    + [(x, y, config.RX_CIRCUIT, config.RX_GROUP, 1 if t > 0 else -1)
       for (x, y, t) in config.RX_LABELS]
)
COIL_MATERIAL = config.COIL_WIRE_BLOCK   # wire material assigned to the coils

def run_sweep():
    """Solve every (turns, current) combination and write the results CSV."""
    print("Starting property-based FEMM sweep (no geometry scaling)...")
    femm.openfemm()   # launch the FEMM process this script drives
    results = []
    try:
        # Full factorial: every turns count against every drive current.
        for turns in turns_sweep:
            for cur in current_sweep:
                print(f"Testing Turns={turns}, Drive={cur} A ...")
                # Reload the pristine base model for every combination, then
                # redirect it to the scratch file. FEMM auto-saves on analyze,
                # so this save-as is what keeps the base model unmodified.
                femm.opendocument(config.FEM_FILE)
                femm.mi_saveas(WORK_FEM)
                # mi_probdef(frequency, units, type, precision, depth,
                #            minangle, acsolver). Frequency > 0 selects the
                # time-harmonic solver; depth must be the real coil axial
                # length so absolute flux/M/voltage are physical, not per-mm.
                # Frequency and depth come from config. The precision (1e-8),
                # minimum mesh angle (30) and acsolver (0) are FEMM numerical
                # settings, not physical parameters, so they stay local.
                femm.mi_probdef(config.FREQUENCY_HZ, "millimeters", "planar",
                                1e-8, config.COIL_DEPTH_MM, 30, 0)
                # Re-stamp the turns count onto each coil half.
                # mi_setblockprop(material, automesh, meshsize, circuit,
                #                 magdir, group, turns) applies to whatever is
                # currently selected, so select the label, set it, clear.
                for (x, y, circuit, group, sign) in COIL_HALVES:
                    femm.mi_selectlabel(x, y)
                    femm.mi_setblockprop(COIL_MATERIAL, 1, 0, circuit, 0, group, sign * turns)
                    femm.mi_clearselected()
                # mi_modifycircprop(circuit, property, value): property 1 is
                # the circuit current, so this sets the TX drive in amps.
                femm.mi_modifycircprop(config.TX_CIRCUIT, 1, cur)
                # Mesh + solve, then open the result for the mo_* readers.
                femm.mi_analyze(1)
                femm.mi_loadsolution()
                # Each call returns [current, voltage, flux_linkage].
                rx = femm.mo_getcircuitproperties(config.RX_CIRCUIT)
                tx = femm.mo_getcircuitproperties(config.TX_CIRCUIT)
                rx_v = abs(rx[1]); rx_flux = abs(rx[2]); tx_i = abs(tx[0])
                # M = RX flux linkage per amp of TX drive, in microhenries.
                M_uH = (rx_flux / tx_i) * 1e6 if tx_i > 0 else 0.0
                results.append([turns, cur, tx_i, rx_flux, M_uH, rx_v])
                femm.mo_close(); femm.mi_close()   # post-processor, then model
    except Exception as e:
        print(f"Error during sweep: {e}")
        import traceback; traceback.print_exc()
    finally:
        femm.closefemm()   # always shut the FEMM process down

    # Only overwrite the CSV when there is something to write, so a failed run
    # does not destroy the previous good data set.
    if not results:
        print("No results collected -- keeping the previous CSV untouched.")
        return
    with open(CSV_OUT, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Turns", "Drive_Current_A", "TX_Current_A", "RX_Flux_Wb",
                    "Mutual_Inductance_uH", "RX_Voltage_V"])
        w.writerows(results)
    print(f"Sweep complete ({len(results)} runs). Data -> {CSV_OUT}")

if __name__ == "__main__":
    run_sweep()
