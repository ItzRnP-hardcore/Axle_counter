"""
Brute-force grid search for the coil pair that maximises the RX signal.

Sweeps frequency, wire radius, primary/secondary coil area and turn count,
applies the drive-voltage, drive-current and wire-length limits below, and
prints the single combination with the largest peak-to-peak secondary voltage
Vs_pp = 2 * w * M * Ip. Analytic only -- no FEMM is run; results go to stdout.

Scaling-law caveat: M ~ N^2 (turns on both coils) IS FEMM-verified, but the
linear-in-area terms (Ap/Ap0) and (As/As0) are an analytic EXTRAPOLATION from
the single FEMM anchor, not a FEMM result. Large area scale factors are
guidance only.

Paths come from config (BASE_DIR / OUTPUT_DIR), not this script's own
directory, because the script lives in a subfolder.
"""
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import time
import config

print("Starting optimizer...")
start_time = time.time()

# Constraints on the drive electronics and the physical build
MAX_VP_PP = 24.0 # 24V peak-to-peak means 12V peak
MAX_VP_PEAK = MAX_VP_PP / 2.0
MAX_IP_PEAK = 5.0 # Amps
MAX_WIRE_LEN = 500.0 # meters per coil

# Constants
mu0 = 4 * np.pi * 1e-7      # permeability of free space (H/m)
rho_copper = 1.68e-8        # copper resistivity (ohm.m)

# Verified FEMM baseline (see config.py): M0 is the measured mutual inductance
# with BASELINE_TURNS turns on both coils and nominal coil area A_REF_M2. Every
# candidate design is scaled away from this anchor. The M ~ N^2 turn law is
# FEMM-verified; the linear-in-area term is an EXTRAPOLATION, so treat large
# area ratios as guidance rather than prediction.
M0 = config.M0_H     # H
Np0 = config.BASELINE_TURNS
Ns0 = config.BASELINE_TURNS
Ap0 = config.A_REF_M2 # m^2, nominal baseline coil area
As0 = config.A_REF_M2 # m^2

# Function for AC resistance
def get_ac_resistance(r_dc, a, freq):
    """Scale a DC resistance up for skin effect at the given frequency.

    At frequency `freq` the current concentrates in a surface layer of depth
    `delta`, so a wire of radius `a` uses less than its full cross-section and
    its resistance rises. `factor` is a standard closed-form approximation of
    that ratio in terms of x = a/delta: a small correction while the wire is
    thinner than one skin depth, growing roughly linearly in x beyond it.
    Proximity effect between neighbouring turns is not modelled.
    """
    delta = np.sqrt(rho_copper / (np.pi * freq * mu0))
    x = a / delta
    if x < 1.0:
        factor = 1.0 + (x**4) / 48.0
    else:
        factor = x / 2.0 + 0.75 + 3.0 / (32.0 * x)
    return r_dc * factor

best_Vs_pp = 0.0
best_params = {}

# Grid Search -- every combination of the lists below is evaluated.
frequencies = [10000, 20000]                 # candidate drive frequencies (Hz)
wire_radii_mm = [0.25, 0.5, 1.0, 1.5, 2.0]   # conductor radius options (mm)
Ap_list = np.linspace(0.01, 0.2, 20)         # primary (TX) coil areas, m^2
As_list = np.linspace(0.01, 0.2, 20)         # secondary (RX) coil areas, m^2

for f in frequencies:
    for a_mm in wire_radii_mm:
        a = a_mm * 1e-3
        for Ap in Ap_list:
            # Treat each coil as a circle of the given area to get its radius,
            # which sets both the wire length per turn and the resistance.
            rp = np.sqrt(Ap / np.pi)
            for As in As_list:
                rs = np.sqrt(As / np.pi)

                # Determine max Np that fits under 500m
                max_Np_len = int(MAX_WIRE_LEN / (2 * np.pi * rp))
                
                # Determine max Ns that fits under 500m
                max_Ns_len = int(MAX_WIRE_LEN / (2 * np.pi * rs))
                
                # Candidate primary turn counts (skip any that need too much wire)
                for Np in [10, 50, 100, 200, 500, 1000, 2000, 3000, 5000]:
                    if Np > max_Np_len: continue

                    lp = Np * 2 * np.pi * rp
                    R_dc = rho_copper * lp / (np.pi * a**2)
                    R_ac = get_ac_resistance(R_dc, a, f)
                    
                    # The drive current is capped either by the amplifier's
                    # current limit or by the voltage it can develop across
                    # the coil resistance -- whichever binds first.
                    Ip_peak_limit_from_voltage = MAX_VP_PEAK / R_ac
                    Ip_peak = min(MAX_IP_PEAK, Ip_peak_limit_from_voltage)

                    # Candidate secondary turn counts (the RX coil carries no
                    # current, so it may run to more turns than the primary)
                    for Ns in [10, 50, 100, 200, 500, 1000, 2000, 3000, 5000, 10000]:
                        if Ns > max_Ns_len: continue

                        # Scale M away from the FEMM anchor: linear in each
                        # coil's turns (together giving the verified N^2 law)
                        # and linear in each coil's area (extrapolated).
                        M = M0 * (Np / Np0) * (Ns / Ns0) * (Ap / Ap0) * (As / As0)

                        # Induced RX voltage: the shared flux M*Ip alternating
                        # at omega induces omega*M*Ip peak, doubled for pk-pk.
                        omega = 2 * np.pi * f
                        Vs_peak = omega * M * Ip_peak
                        Vs_pp = 2 * Vs_peak

                        # Keep the running best design.
                        if Vs_pp > best_Vs_pp:
                            best_Vs_pp = Vs_pp
                            best_params = {
                                'Frequency_kHz': f / 1e3,
                                'Wire_Radius_mm': a_mm,
                                'Primary_Area_m2': Ap,
                                'Secondary_Area_m2': As,
                                'Primary_Turns': Np,
                                'Secondary_Turns': Ns,
                                'Ip_peak_A': Ip_peak,
                                'Vp_peak_V': Ip_peak * R_ac,
                                'M_uH': M * 1e6,
                                'Primary_Wire_Len_m': lp,
                                'Secondary_Wire_Len_m': Ns * 2 * np.pi * rs
                            }

print(f"Optimization finished in {time.time() - start_time:.2f} seconds.")
print("=== BEST CONFIGURATION FOUND ===")
print(f"Max Secondary Voltage (Vs_pp): {best_Vs_pp:.4f} V")
for k, v in best_params.items():
    if isinstance(v, float):
        print(f"{k}: {v:.4f}")
    else:
        print(f"{k}: {v}")
