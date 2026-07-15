import numpy as np

mu0 = 4 * np.pi * 1e-7
f = 20000
omega = 2 * np.pi * f
a = 1.5e-3  # wire radius

scenarios = [
    {"name": "Scenario 1 (Small Coil)", "N": 300, "Area": 0.05, "Ip_peak": 5.0},
    {"name": "Scenario 2 (Fewest Turns)", "N": 100, "Area": 0.15, "Ip_peak": 5.0},
    {"name": "Scenario 3 (Max Signal)", "N": 300, "Area": 0.15, "Ip_peak": 5.0}
]

for s in scenarios:
    r = np.sqrt(s["Area"] / np.pi)
    L = mu0 * (s["N"]**2) * r * (np.log((8 * r) / a) - 2.0)
    C = 1.0 / (omega**2 * L)
    
    # Voltage across the capacitor at resonance is V_c = I_peak * omega * L
    Vc_peak = s["Ip_peak"] * omega * L
    
    print(f"{s['name']}:")
    print(f"  Inductance L = {L*1e3:.4f} mH")
    print(f"  Capacitor C = {C*1e9:.2f} nF")
    print(f"  Capacitor Voltage Rating = {Vc_peak:.2f} V peak ({(Vc_peak*2)/1000:.2f} kVpp)")
    print()
