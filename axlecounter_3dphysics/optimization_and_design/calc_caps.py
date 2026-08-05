"""Resonant capacitor / voltage-rating check for three candidate coil scenarios.

For each scenario this computes the coil's self-inductance, the capacitance
needed to resonate it at config.FREQUENCY_HZ, and the peak voltage that
capacitor must withstand -- which is what decides whether an off-the-shelf
part exists. Prints to stdout; nothing is written to disk.

Standalone analytic helper -- no FEMM. Uses the single-loop inductance formula
that the rest of the repo uses, so the numbers line up with summary.py and
generate_data_points.py. Reads its operating frequency from config rather than
hardcoding it.
"""
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import config

mu0 = config.MU0                 # permeability of free space (H/m), from config
f = config.FREQUENCY_HZ          # operating frequency (Hz), from config
omega = config.OMEGA             # angular frequency (rad/s) at f, from config
a = config.WIRE_RADIUS_M         # wire radius: the canonical 18 AWG conductor

# Three coil designs to compare: turns N, enclosed area (m^2) and the peak
# drive current they would carry.
#
# Nothing here is an independent number any more. The areas are the reference
# coil area A_REF_M2 multiplied by scale factors taken from the config study
# grid AREA_SCALE_SWEEP, so a scenario can never drift away from the canonical
# coil; the 1:3 small-to-large area ratio of the original scenarios is kept by
# picking the 5x and 15x entries. The turn counts come from the canonical turn
# grid TURNS_SWEEP, and the drive current from the analytic current limit.
AREA_SCALE_SMALL = config.AREA_SCALE_SWEEP[1]    # 5x  the reference coil area
AREA_SCALE_LARGE = config.AREA_SCALE_SWEEP[3]    # 15x the reference coil area
N_FEW = config.TURNS_SWEEP[1]                    # 100 turns
N_MANY = config.TURNS_SWEEP[4]                   # 300 turns
Ip_peak = config.MAX_DRIVE_CURRENT_A             # A peak
scenarios = [
    {"name": "Scenario 1 (Small Coil)", "N": N_MANY,
     "Area": config.A_REF_M2 * AREA_SCALE_SMALL, "Ip_peak": Ip_peak},
    {"name": "Scenario 2 (Fewest Turns)", "N": N_FEW,
     "Area": config.A_REF_M2 * AREA_SCALE_LARGE, "Ip_peak": Ip_peak},
    {"name": "Scenario 3 (Max Signal)", "N": N_MANY,
     "Area": config.A_REF_M2 * AREA_SCALE_LARGE, "Ip_peak": Ip_peak}
]

for s in scenarios:
    # Radius of a circle with the given enclosed area.
    r = np.sqrt(s["Area"] / np.pi)
    # Self-inductance of an N-turn circular air coil (single-loop formula).
    L = mu0 * (s["N"]**2) * r * (np.log((8 * r) / a) - 2.0)
    # Capacitance that resonates with L at omega: C = 1 / (omega^2 * L).
    C = 1.0 / (omega**2 * L)

    # At resonance the coil's reactance omega*L and the capacitor's cancel in
    # the loop, but each individually still carries the full circulating
    # current, so the capacitor sees V_c = I_peak * omega * L. This is the
    # number that sets the required voltage rating.
    Vc_peak = s["Ip_peak"] * omega * L

    print(f"{s['name']}:")
    print(f"  Inductance L = {L*1e3:.4f} mH")
    print(f"  Capacitor C = {C*1e9:.2f} nF")
    print(f"  Capacitor Voltage Rating = {Vc_peak:.2f} V peak ({(Vc_peak*2)/1000:.2f} kVpp)")
    print()
