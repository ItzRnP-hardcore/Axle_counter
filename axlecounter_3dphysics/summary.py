"""Operating-point summary for a scaled-up coil pair.

The old version hardcoded M = 3.4267 uH and labelled it "from FEMM". It was
actually an analytic extrapolation built on a stale DC anchor and a wrong
Ns0=60 baseline. This version derives M transparently from the VERIFIED FEMM
anchor in config.py and prints the scaling assumptions it uses.

CAVEAT: the area term of the scaling law is an extrapolation (see config.py);
at the large scale factors used here, treat the absolute numbers as
order-of-magnitude design guidance, not validated predictions.
"""
import os
import sys

import numpy as np

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import config

mu0 = 4 * np.pi * 1e-7
rho_copper = 1.68e-8

# Target + design point
V_s_pp = 3.3
V_s_peak = V_s_pp / 2.0
N_s = 200
A_s = 0.2
r_s = np.sqrt(A_s / np.pi)
N_p = 200
A_p = 0.2
r_p = np.sqrt(A_p / np.pi)
wire_radius = 1.5e-3

# Analytic M, anchored to the verified FEMM baseline
N0 = config.BASELINE_TURNS
A0 = config.A_REF_M2
M_scaled = config.M0_H * (N_p / N0) * (N_s / N0) * (A_p / A0) * (A_s / A0)

L_p = mu0 * (N_p**2) * r_p * (np.log((8 * r_p) / wire_radius) - 2.0)
L_s = mu0 * (N_s**2) * r_s * (np.log((8 * r_s) / wire_radius) - 2.0)
k = M_scaled / np.sqrt(L_p * L_s)

print(f"FEMM anchor M0: {config.M0_UH:.4f} uH at {N0}/{N0} turns "
      f"({config.FREQUENCY_HZ/1e3:.0f} kHz)")
print(f"Scaled design point: Np=Ns={N_p}, Ap=As={A_p} m^2 "
      f"(area scale ~{A_p/A0:.1f}x per coil -- extrapolated)")
print(f"Analytic Mutual Inductance: {M_scaled*1e6:.2f} uH")
print(f"Coupling Coefficient k: {k:.2e}" +
      ("  (WARNING: k>1 is unphysical -- scaling law broke down)" if k >= 1 else ""))


def get_ac_resistance(r_dc, a, freq):
    delta = np.sqrt(rho_copper / (np.pi * freq * mu0))
    x = a / delta
    if x < 1.0:
        factor = 1.0 + (x**4) / 48.0
    else:
        factor = x / 2.0 + 0.75 + 3.0 / (32.0 * x)
    return r_dc * factor, delta


l_wire_p = N_p * 2 * np.pi * r_p
A_wire = np.pi * (wire_radius**2)
R_p_dc = rho_copper * l_wire_p / A_wire

for f in [10000, 20000]:
    omega = 2 * np.pi * f
    R_p_ac, delta = get_ac_resistance(R_p_dc, wire_radius, f)

    I_p_peak = V_s_peak / (omega * M_scaled)
    I_p_rms = I_p_peak / np.sqrt(2)
    X_p = omega * L_p
    Z_p = np.sqrt(R_p_ac**2 + X_p**2)
    V_p_peak = I_p_peak * Z_p
    V_p_pp = 2 * V_p_peak
    C_p = 1.0 / (omega**2 * L_p)
    V_p_peak_res = I_p_peak * R_p_ac
    V_p_pp_res = 2 * V_p_peak_res

    print(f"\nFor 3.3Vpp at {f/1e3:.1f} kHz Sine Wave:")
    print(f"Required Primary Current: {I_p_peak:.3f} A peak (RMS: {I_p_rms:.3f} A)")
    print(f"Required Primary Voltage (Uncompensated): {V_p_pp:.2f} Vpp")
    print(f"Resonant Capacitor C_p: {C_p*1e9:.2f} nF")
    print(f"Required Primary Voltage (Resonant): {V_p_pp_res:.4f} Vpp")
