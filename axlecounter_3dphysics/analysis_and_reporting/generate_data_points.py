"""Analytic sweep of turns / coil-area scale -> M, drive V, secondary V.

For each (turns, area scale) combination the script scales the mutual
inductance away from the FEMM baseline, then works out what it takes to drive
the primary at the configured current ceiling (config.MAX_DRIVE_CURRENT_A) and
what secondary voltage that induces.

Anchored to the VERIFIED FEMM baseline: config.M0_UH is the mutual inductance
measured with BASELINE_TURNS turns on BOTH coils, solved time-harmonic at
config.FREQUENCY_HZ.

CAVEAT: the area term (M linear in each coil's area at fixed separation) is
an analytic EXTRAPOLATION, not a FEMM result. Turn scaling (M ~ N^2) IS
verified by the FEMM property sweep. Treat large area scale factors as
order-of-magnitude guidance only.

Writes reports/coil_parameter_sweep.csv (one row per combination).
"""
import sys, os

# Paths come from config (BASE_DIR / OUTPUT_DIR), not from this script's own
# directory -- the script lives in a subfolder of the project.
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import os
import numpy as np
import pandas as pd
import config

# Physical constants: permeability of free space, resistivity of copper.
# Both come from config so every script in the project uses one definition.
mu0 = config.MU0
rho_copper = config.RHO_COPPER
f = config.FREQUENCY_HZ
omega = config.OMEGA

# Verified FEMM anchor (see config.py)
M0 = config.M0_H            # H, at N0 turns on both coils, area scale 1.0
N0 = config.BASELINE_TURNS
A0 = config.A_REF_M2        # nominal per-coil area at scale 1.0

data = []

# Sweep Parameters -- the canonical grids and the canonical 18 AWG conductor,
# all taken from config so this sweep covers the same points as femm_sweep.py.
turns_list = config.TURNS_SWEEP
area_scale_list = config.AREA_SCALE_SWEEP
a = config.WIRE_RADIUS_M


def get_ac_resistance(r_dc, a, freq):
    """Scale a DC wire resistance up for the skin effect at `freq`.

    At AC the current crowds into a surface layer of thickness `delta` (the
    skin depth), shrinking the effective conducting cross-section. When the
    wire radius `a` is much smaller than delta the correction is negligible;
    once a > delta the resistance grows roughly linearly with a/delta.
    """
    delta = np.sqrt(rho_copper / (np.pi * freq * mu0))
    x = a / delta
    if x < 1.0:
        factor = 1.0 + (x**4) / 48.0
    else:
        factor = x / 2.0 + 0.75 + 3.0 / (32.0 * x)
    return r_dc * factor


for turns in turns_list:
    for scale in area_scale_list:
        # Scaled coil area, and the equivalent circular-coil radius.
        Ap = A0 * scale
        rp = np.sqrt(Ap / np.pi)

        # M ~ N^2 (FEMM-verified) x area scale on each coil (extrapolated)
        M = M0 * (turns / N0) ** 2 * scale * scale

        # We limit primary current to the configured ceiling (A peak)
        Ip_peak = config.MAX_DRIVE_CURRENT_A

        # Drive voltage at resonance. A series capacitor cancels the coil's
        # inductive reactance, so only the AC wire resistance is left to push
        # current through. lp is the total wire length (turns x circumference).
        lp = turns * 2 * np.pi * rp
        R_dc = rho_copper * lp / (np.pi * a**2)
        R_ac = get_ac_resistance(R_dc, a, f)

        Vp_peak = Ip_peak * R_ac
        Vp_pp = Vp_peak * 2

        # Faraday's law: the open-circuit voltage induced in the secondary is
        # the rate of change of linked flux, i.e. omega * M * I_primary.
        Vs_peak = omega * M * Ip_peak
        Vs_pp = 2 * Vs_peak

        data.append({
            'Coil_Turns (Np=Ns)': turns,
            'Area_Scale_Factor': scale,
            'Primary_Area_m2': Ap,
            'Mutual_Inductance_uH': M * 1e6,
            'Primary_Current_Peak_A': Ip_peak,
            'Required_Primary_Voltage_Vpp': Vp_pp,
            'Resulting_Secondary_Voltage_Vpp': Vs_pp
        })

df = pd.DataFrame(data)
out_path = os.path.join(config.OUTPUT_DIR, 'coil_parameter_sweep.csv')
df.to_csv(out_path, index=False)
print(f"Data points saved to {out_path}")
