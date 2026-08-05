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

mu0 = 4 * np.pi * 1e-7           # permeability of free space (H/m)
f = config.FREQUENCY_HZ          # operating frequency (Hz), from config
omega = 2 * np.pi * f            # angular frequency (rad/s)
a = 1.5e-3  # wire radius

# Three coil designs to compare: turns N, enclosed area (m^2) and the peak
# drive current they would carry.
scenarios = [
    {"name": "Scenario 1 (Small Coil)", "N": 300, "Area": 0.05, "Ip_peak": 5.0},
    {"name": "Scenario 2 (Fewest Turns)", "N": 100, "Area": 0.15, "Ip_peak": 5.0},
    {"name": "Scenario 3 (Max Signal)", "N": 300, "Area": 0.15, "Ip_peak": 5.0}
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
