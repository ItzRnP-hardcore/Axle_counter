import os
import numpy as np
import pandas as pd
import config

# Constants
mu0 = 4 * np.pi * 1e-7
rho_copper = 1.68e-8
f = 20000 # 20 kHz
omega = 2 * np.pi * f

# Baseline from FEMM
# Using the 1.5x scaled FEMM file baseline M
M0_scaled = 0.00771e-6 # Wait, earlier output showed 0.007712 uH for the 1.5x scale
# Actually, the 1.5x scale didn't change the block properties area, but let's just use the analytical M base we used in optimizer:
M0 = 0.00771e-6
Np0 = 100
Ns0 = 60
Ap0 = 0.01
As0 = 0.06

def get_ac_resistance(r_dc, a, freq):
    delta = np.sqrt(rho_copper / (np.pi * freq * mu0))
    x = a / delta
    if x < 1.0:
        factor = 1.0 + (x**4) / 48.0
    else:
        factor = x / 2.0 + 0.75 + 3.0 / (32.0 * x)
    return r_dc * factor

data = []

# Sweep Parameters
turns_list = [50, 100, 150, 200, 300, 400]
area_scale_list = [1.0, 5.0, 10.0, 15.0, 20.0]
wire_radius_mm = 1.5
a = wire_radius_mm * 1e-3

for turns in turns_list:
    for scale in area_scale_list:
        Ap = Ap0 * scale
        As = As0 * scale
        rp = np.sqrt(Ap / np.pi)
        
        # Calculate M
        M = M0 * (turns / Np0) * (turns / Ns0) * (Ap / Ap0) * (As / As0)
        
        # We limit primary current to 5A
        Ip_peak = 5.0
        
        # Calculate required voltage at resonance to push 5A
        lp = turns * 2 * np.pi * rp
        R_dc = rho_copper * lp / (np.pi * a**2)
        R_ac = get_ac_resistance(R_dc, a, f)
        
        Vp_peak = Ip_peak * R_ac
        Vp_pp = Vp_peak * 2
        
        # Resulting Secondary Voltage
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
# Save to the artifacts directory so the user can easily see it
out_path = os.path.join(config.OUTPUT_DIR, 'coil_parameter_sweep.csv')
df.to_csv(out_path, index=False)
print(f"Data points saved to {out_path}")
