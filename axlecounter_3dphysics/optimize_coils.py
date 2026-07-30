import numpy as np
import time
import config

print("Starting optimizer...")
start_time = time.time()

# Constraints
MAX_VP_PP = 24.0 # 24V peak-to-peak means 12V peak
MAX_VP_PEAK = MAX_VP_PP / 2.0
MAX_IP_PEAK = 5.0 # Amps
MAX_WIRE_LEN = 500.0 # meters per coil

# Constants
mu0 = 4 * np.pi * 1e-7
rho_copper = 1.68e-8

# Verified FEMM baseline (see config.py). The old version used a stale DC
# value of 0.00771e-6 and Ns0=60 despite the model having 100 turns on both
# coils. M ~ N^2 is FEMM-verified; the linear-in-area term is extrapolated.
M0 = config.M0_H     # H
Np0 = config.BASELINE_TURNS
Ns0 = config.BASELINE_TURNS
Ap0 = config.A_REF_M2 # m^2, nominal baseline coil area
As0 = config.A_REF_M2 # m^2

# Function for AC resistance
def get_ac_resistance(r_dc, a, freq):
    delta = np.sqrt(rho_copper / (np.pi * freq * mu0))
    x = a / delta
    if x < 1.0:
        factor = 1.0 + (x**4) / 48.0
    else:
        factor = x / 2.0 + 0.75 + 3.0 / (32.0 * x)
    return r_dc * factor

best_Vs_pp = 0.0
best_params = {}

# Grid Search
frequencies = [10000, 20000]
wire_radii_mm = [0.25, 0.5, 1.0, 1.5, 2.0]
Ap_list = np.linspace(0.01, 0.2, 20)
As_list = np.linspace(0.01, 0.2, 20)

for f in frequencies:
    for a_mm in wire_radii_mm:
        a = a_mm * 1e-3
        for Ap in Ap_list:
            rp = np.sqrt(Ap / np.pi)
            for As in As_list:
                rs = np.sqrt(As / np.pi)
                
                # Determine max Np that fits under 500m
                max_Np_len = int(MAX_WIRE_LEN / (2 * np.pi * rp))
                
                # Determine max Ns that fits under 500m
                max_Ns_len = int(MAX_WIRE_LEN / (2 * np.pi * rs))
                
                for Np in [10, 50, 100, 200, 500, 1000, 2000, 3000, 5000]:
                    if Np > max_Np_len: continue
                    
                    lp = Np * 2 * np.pi * rp
                    R_dc = rho_copper * lp / (np.pi * a**2)
                    R_ac = get_ac_resistance(R_dc, a, f)
                    
                    Ip_peak_limit_from_voltage = MAX_VP_PEAK / R_ac
                    Ip_peak = min(MAX_IP_PEAK, Ip_peak_limit_from_voltage)
                    
                    for Ns in [10, 50, 100, 200, 500, 1000, 2000, 3000, 5000, 10000]:
                        if Ns > max_Ns_len: continue
                        
                        # Calculate Mutual Inductance based on scaling laws
                        M = M0 * (Np / Np0) * (Ns / Ns0) * (Ap / Ap0) * (As / As0)
                        
                        # Calculate Secondary Voltage
                        omega = 2 * np.pi * f
                        Vs_peak = omega * M * Ip_peak
                        Vs_pp = 2 * Vs_peak
                        
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
