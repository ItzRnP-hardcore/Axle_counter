"""Operating-point summary for a scaled-up coil pair.

Takes one hypothetical design point (config.DESIGN_TURNS turns and
config.DESIGN_AREA_M2 on each coil), derives its mutual inductance from the
VERIFIED FEMM anchor in config.py, and prints what it would take to hit the
config.DESIGN_TARGET_VPP signal at the receiver: primary current,
uncompensated drive voltage, resonant capacitor value, and the much smaller
drive voltage needed once that capacitor is fitted. Console output only --
nothing is written to disk.

The turn-scaling law M ~ N^2 is FEMM-verified. CAVEAT: the area term of the
scaling law is an analytic EXTRAPOLATION, not a FEMM result (see config.py);
at the large scale factors used here, treat the absolute numbers as
order-of-magnitude design guidance, not validated predictions.
"""
import os
import sys

import numpy as np

# Paths and the FEMM anchor come from config, not from this script's own
# directory -- the script lives in a subfolder of the project.
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

# Material constants come from config -- one definition for the whole project.
mu0 = config.MU0
rho_copper = config.RHO_COPPER

# Target signal at the receiver, and the coil design point being evaluated.
# Subscript p = primary (TX), s = secondary (RX). Each coil is treated as a
# circle of area A, so r = sqrt(A/pi). The design point (turns, area, target
# voltage) and the 18 AWG wire radius all come from config.
V_s_pp = config.DESIGN_TARGET_VPP
V_s_peak = V_s_pp / 2.0
N_s = config.DESIGN_TURNS
A_s = config.DESIGN_AREA_M2
r_s = np.sqrt(A_s / np.pi)
N_p = config.DESIGN_TURNS
A_p = config.DESIGN_AREA_M2
r_p = np.sqrt(A_p / np.pi)
wire_radius = config.WIRE_RADIUS_M

# Analytic M, anchored to the verified FEMM baseline: scale the measured M0
# by turns on each coil (verified) and by area on each coil (extrapolated).
N0 = config.BASELINE_TURNS
A0 = config.A_REF_M2
M_scaled = config.M0_H * (N_p / N0) * (N_s / N0) * (A_p / A0) * (A_s / A0)

# Self-inductance of a single circular loop of radius r wound N times, from
# the standard thin-wire formula. Valid while the wire is much thinner than
# the coil radius.
L_p = mu0 * (N_p**2) * r_p * (np.log((8 * r_p) / wire_radius) - 2.0)
L_s = mu0 * (N_s**2) * r_s * (np.log((8 * r_s) / wire_radius) - 2.0)

# Coupling coefficient: the fraction of one coil's flux that reaches the
# other. Physically it must lie in [0, 1]; k >= 1 means the extrapolated M
# has outrun what the geometry can support.
k = M_scaled / np.sqrt(L_p * L_s)

print(f"FEMM anchor M0: {config.M0_UH:.4f} uH at {N0}/{N0} turns "
      f"({config.FREQUENCY_HZ/1e3:.0f} kHz)")
print(f"Scaled design point: Np=Ns={N_p}, Ap=As={A_p:.4f} m^2 "
      f"(area scale ~{A_p/A0:.1f}x per coil -- extrapolated)")
print(f"Analytic Mutual Inductance: {M_scaled*1e6:.2f} uH")
print(f"Coupling Coefficient k: {k:.2e}" +
      ("  (WARNING: k>1 is unphysical -- scaling law broke down)" if k >= 1 else ""))


def get_ac_resistance(r_dc, a, freq):
    """Scale a DC wire resistance up for the skin effect; returns (R_ac, delta).

    `delta` is the skin depth: at AC the current concentrates in a surface
    layer of about this thickness, so the effective conducting area shrinks.
    Below a = delta the correction is negligible; above it, resistance grows
    roughly linearly with a/delta.
    """
    delta = np.sqrt(rho_copper / (np.pi * freq * mu0))
    x = a / delta
    if x < 1.0:
        factor = 1.0 + (x**4) / 48.0
    else:
        factor = x / 2.0 + 0.75 + 3.0 / (32.0 * x)
    return r_dc * factor, delta


# Total primary wire length (turns x circumference) and its DC resistance.
l_wire_p = N_p * 2 * np.pi * r_p
A_wire = np.pi * (wire_radius**2)
R_p_dc = rho_copper * l_wire_p / A_wire

# Compare the two candidate operating frequencies: the bottom of the swept
# band and the canonical operating point, both from config.
for f in [config.FREQ_SWEEP_START_HZ, config.FREQUENCY_HZ]:
    omega = 2 * np.pi * f
    R_p_ac, delta = get_ac_resistance(R_p_dc, wire_radius, f)

    # Invert Faraday's law V_s = omega * M * I_p to get the primary current
    # needed for the target receiver voltage.
    I_p_peak = V_s_peak / (omega * M_scaled)
    I_p_rms = I_p_peak / np.sqrt(2)

    # Uncompensated drive: the source fights the full coil impedance, which
    # at these frequencies is dominated by the inductive reactance omega*L.
    X_p = omega * L_p
    Z_p = np.sqrt(R_p_ac**2 + X_p**2)
    V_p_peak = I_p_peak * Z_p
    V_p_pp = 2 * V_p_peak

    # Series resonance: choosing C so that 1/(omega*C) = omega*L cancels the
    # reactance, leaving only R_ac -- hence a far smaller drive voltage.
    C_p = 1.0 / (omega**2 * L_p)
    V_p_peak_res = I_p_peak * R_p_ac
    V_p_pp_res = 2 * V_p_peak_res

    print(f"\nFor {V_s_pp}Vpp at {f/1e3:.1f} kHz Sine Wave:")
    print(f"Required Primary Current: {I_p_peak:.3f} A peak (RMS: {I_p_rms:.3f} A)")
    print(f"Required Primary Voltage (Uncompensated): {V_p_pp:.2f} Vpp")
    print(f"Resonant Capacitor C_p: {C_p*1e9:.2f} nF")
    print(f"Required Primary Voltage (Resonant): {V_p_pp_res:.4f} Vpp")
