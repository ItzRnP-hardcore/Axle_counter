import os
import nbformat as nbf

def build_notebook(artifacts_dir):
    nb = nbf.v4.new_notebook()

    # Introduction Markdown
    intro_md = """# Axle Counter: Primary Coil Parameter Calculations
This notebook calculates the electrical and physical parameters of the primary transmitter coil for an axle counter system.

## Design Specifications
* **Target Secondary Voltage ($Vs$):** $3.3\\text{ V}_{p-p}$ (Peak-to-Peak)
* **Secondary Coil Turns ($Ns$):** $200$ turns
* **Secondary Coil Area ($As$):** $2000\\text{ cm}^2 = 0.2\\text{ m}^2$ (Radius $rs \\approx 25.2\\text{ cm}$)
* **Mutual Inductance ($M$):** Scaled analytically from FEMM optimizations to $3.4267\\text{ }\\mu\\text{H}$.
* **Operating Frequency ($f$):** $10\\text{ kHz}$ to $20\\text{ kHz}$
* **Waveforms:** Sine Wave and Square Wave

## Assumed Primary Coil Parameters
* **Primary Coil Turns ($Np$):** $200$ turns
* **Primary Coil Area ($Ap$):** $2000\\text{ cm}^2 = 0.2\\text{ m}^2$ (Radius $rp \\approx 25.2\\text{ cm}$)
* **Wire Details:** copper wire, radius $a = 1.5\\text{ mm}$ (approx 9 AWG)
"""

    # Imports and Constants Code
    constants_code = """import numpy as np
import matplotlib.pyplot as plt
import os
import sys

# Load optimal configuration from the physics suite
sys.path.append("c:\\\\Users\\\\rudra\\\\Axle_counter\\\\axlecounter_3dphysics")
import config

# Physical constants
mu0 = 4 * np.pi * 1e-7  # Permeability of free space (H/m)
rho_copper = 1.68e-8   # Resistivity of copper (Ohm-m)

# Given parameters
V_s_pp = 3.3           # Target secondary peak-to-peak voltage (V)
V_s_peak = V_s_pp / 2.0 # Target secondary peak voltage (V)
N_s = 200              # Secondary turns
A_s = 0.2              # Secondary area (m^2)
r_s = np.sqrt(A_s / np.pi) # Secondary radius (m)

# Extract optimal M based on analytical scaling from FEMM
M_femm = 3.4267e-6


# Assumed primary parameters
N_p = 200              # Primary turns
A_p = 0.2              # Primary area (m^2)
r_p = np.sqrt(A_p / np.pi) # Primary radius (m)
wire_radius = 1.5e-3   # Wire radius (m) for 3mm diameter wire

# Artifacts output path passed from script
artifacts_dir = "{artifacts_dir}"
os.makedirs(artifacts_dir, exist_ok=True)

print(f"Primary Coil Radius: {r_p*100:.2f} cm")
print(f"Secondary Coil Radius: {r_s*100:.2f} cm")
""".replace('{artifacts_dir}', artifacts_dir.replace('\\', '\\\\'))

    # Inductance Calculation Markdown
    inductance_md = """## 1. Inductance & Coupling Calculations
We calculate the self-inductances $L_p$ and $L_s$ using the standard loop formula for a multi-turn thin circular coil:
$$L \\approx \\mu_0 N^2 r \\left( \\ln\\left(\\frac{8r}{a}\\right) - 2 \\right)$$

For the mutual inductance $M$, we directly use the value optimized and extracted from the FEMM 3D simulations:
$$M = M_{FEMM}$$
"""

    # Inductance Calculation Code
    inductance_code = """# Calculate self-inductances
L_p = mu0 * (N_p**2) * r_p * (np.log((8 * r_p) / wire_radius) - 2.0)
L_s = mu0 * (N_s**2) * r_s * (np.log((8 * r_s) / wire_radius) - 2.0)

# Calculate coupling coefficient just for reference
k_femm = M_femm / np.sqrt(L_p * L_s)

print(f"Primary Inductance L_p: {L_p*1e3:.4f} mH")
print(f"Secondary Inductance L_s: {L_s*1e3:.4f} mH")
print(f"Optimal Mutual Inductance from FEMM: {M_femm*1e6:.4f} uH")
print(f"Resulting Coupling Coefficient (k): {k_femm:.2e}")
"""

    # Resistance and Skin Effect Code
    resistance_code = """# Resistance Calculations including Skin Effect
def get_ac_resistance(r_dc, a, freq):
    # Skin depth
    delta = np.sqrt(rho_copper / (np.pi * freq * mu0))
    x = a / delta
    if x < 1.0:
        factor = 1.0 + (x**4) / 48.0
    else:
        factor = x / 2.0 + 0.75 + 3.0 / (32.0 * x)
    return r_dc * factor, delta

# Primary Wire Length and DC Resistance
l_wire_p = N_p * 2 * np.pi * r_p
A_wire = np.pi * (wire_radius**2)
R_p_dc = rho_copper * l_wire_p / A_wire

print(f"Primary Wire Length: {l_wire_p:.2f} m")
print(f"Primary DC Resistance R_p_dc: {R_p_dc:.4f} Ohm")
"""

    # Sine Wave Markdown
    sine_md = """## 2. Sine Wave Excitation (10 kHz - 20 kHz)
Under sinusoidal excitation at frequency $f$, the relationship between primary peak current $I_{p, peak}$ and secondary peak voltage $V_{s, peak}$ is:
$$V_{s, peak} = \\omega M I_{p, peak} = 2\\pi f M I_{p, peak}$$
$$I_{p, peak} = \\frac{V_{s, peak}}{2\\pi f M}$$

The driving voltage required on the primary is:
$$V_{p, peak} = I_{p, peak} |Z_p| = I_{p, peak} \\sqrt{R_{p, AC}^2 + (2\\pi f L_p)^2}$$

### Resonant Matching
To reduce the required driving voltage, we can connect a capacitor in series with the primary to resonate at frequency $f$:
$$C_p = \\frac{1}{(2\\pi f)^2 L_p}$$
At resonance, the reactive impedance cancels out, and the required voltage drops to:
$$V_{p, peak, res} = I_{p, peak} R_{p, AC}$$
"""

    # Sine Wave Code
    sine_code = """frequencies = [10000, 20000] # 10 kHz and 20 kHz
M_to_use = M_femm # Using the actual Mutual Inductance from our FEMM simulations

print("=== Sinusoidal Excitation Analysis (Based on FEMM M) ===")
for f in frequencies:
    omega = 2 * np.pi * f
    # AC resistance
    R_p_ac, delta = get_ac_resistance(R_p_dc, wire_radius, f)
    # Peak primary current
    I_p_peak = V_s_peak / (omega * M_to_use)
    I_p_rms = I_p_peak / np.sqrt(2)
    # Uncompensated primary impedance
    X_p = omega * L_p
    Z_p = np.sqrt(R_p_ac**2 + X_p**2)
    V_p_peak = I_p_peak * Z_p
    V_p_pp = 2 * V_p_peak
    # Resonant capacitor
    C_p = 1.0 / (omega**2 * L_p)
    # Resonant voltage
    V_p_peak_res = I_p_peak * R_p_ac
    V_p_pp_res = 2 * V_p_peak_res
    
    print(f"\\nFrequency: {f/1e3:.1f} kHz (Skin depth: {delta*1e3:.4f} mm, R_ac: {R_p_ac:.4f} Ohm)")
    print(f"  Required Primary Peak Current: {I_p_peak:.2f} A (RMS: {I_p_rms:.2f} A)")
    print(f"  Uncompensated driving voltage: {V_p_pp/1e3:.2f} kVpp (Peak: {V_p_peak/1e3:.2f} kV)")
    print(f"  Resonant Capacitor (Series C_p): {C_p*1e9:.2f} nF")
    print(f"  Resonant driving voltage: {V_p_pp_res:.2f} Vpp (Peak: {V_p_peak_res:.2f} V)")
"""

    # Square Wave Markdown
    square_md = """## 3. Square Wave Excitation (10 kHz - 20 kHz)
We analyze two common methods of driving the primary with a square wave:

### Case 1: Square Wave Voltage (Inductance Dominated)
If the primary is driven by a square-wave voltage of amplitude $\\pm V_{p, peak}$:
$$V_p(t) \\approx L_p \\frac{dI_p}{dt}$$
This induces a square-wave voltage on the secondary:
$$V_s(t) = -M \\frac{dI_p}{dt} = -\\frac{M}{L_p} V_p(t)$$
Therefore:
$$V_{p, p-p} = \\frac{L_p}{M} V_{s, p-p}$$
The primary current is a triangular wave with peak value:
$$I_{p, peak} = \\frac{V_{p, peak}}{4 f L_p} = \\frac{V_{s, peak}}{4 f M}$$

### Case 2: Square Wave Current with Finite Rise Time ($t_r$)
If we drive a square-wave current through the primary with a finite transition time $t_r$:
$$V_s(t) = -M \\frac{dI_p}{dt}$$
During transitions, $\\frac{dI_p}{dt} \\approx \\frac{2 I_{p, peak}}{t_r}$, generating voltage spikes on the secondary:
$$V_{s, peak} = M \\frac{2 I_{p, peak}}{t_r} \\implies I_{p, peak} = \\frac{V_{s, peak} t_r}{2 M}$$
The primary voltage required during the transition is:
$$V_{p, peak} = L_p \\frac{2 I_{p, peak}}{t_r} + R_{p, AC} I_{p, peak}$$
"""

    # Square Wave Code
    square_code = """t_r = 1.0e-6 # Assumed rise time of 1 us

print("=== Square Wave Excitation Analysis (Based on FEMM M) ===")
# Case 1: Square Wave Voltage
V_p_pp_sq_v = (L_p / M_to_use) * V_s_pp
print(f"Case 1: Square Wave Voltage Drive (Inductance Dominated):")
print(f"  Required Primary Voltage: {V_p_pp_sq_v/1e3:.2f} kVpp (Constant over frequency)")

for f in frequencies:
    I_p_peak_sq_v = V_s_peak / (4 * f * M_to_use)
    print(f"  At {f/1e3:.1f} kHz:")
    print(f"    Required Peak Current (Triangular): {I_p_peak_sq_v:.2f} A")

# Case 2: Square Wave Current Drive with rise time t_r
print(f"\\nCase 2: Square Wave Current Drive with rise time t_r = {t_r*1e6:.1f} us:")
for f in frequencies:
    R_p_ac, _ = get_ac_resistance(R_p_dc, wire_radius, f)
    I_p_peak_sq_i = (V_s_peak * t_r) / (2 * M_to_use)
    V_p_peak_sq_i = L_p * (2 * I_p_peak_sq_i / t_r) + R_p_ac * I_p_peak_sq_i
    
    print(f"  At {f/1e3:.1f} kHz:")
    print(f"    Required Peak Current: {I_p_peak_sq_i:.2f} A")
    print(f"    Required Peak Primary Voltage (during transition): {V_p_peak_sq_i:.2f} V")
"""

    # Waveform Plot Code
    plot_code = """# Generate Waveform Visualizations for 10 kHz
f = 10000
T = 1.0 / f
t = np.linspace(0, 2*T, 1000)

# 1. Sine Wave Waveforms
omega = 2 * np.pi * f
I_p_sine = (V_s_peak / (omega * M_to_use)) * np.sin(omega * t)
V_s_sine = -M_to_use * (V_s_peak / (omega * M_to_use)) * omega * np.cos(omega * t)

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6), sharex=True)
ax1.plot(t * 1e6, I_p_sine, 'b-', label='Primary Current $I_p(t)$')
ax1.set_ylabel('Primary Current (A)', color='b')
ax1.tick_params(axis='y', labelcolor='b')
ax1.grid(True)
ax1.set_title(f'Sinusoidal Excitation at {f/1e3:.1f} kHz')

ax2.plot(t * 1e6, V_s_sine, 'r-', label='Secondary Voltage $V_s(t)$')
ax2.set_ylabel('Secondary Voltage (V)', color='r')
ax2.tick_params(axis='y', labelcolor='r')
ax2.set_xlabel('Time (us)')
ax2.grid(True)

plt.tight_layout()
sine_plot_path = os.path.join(artifacts_dir, 'sine_wave_comparison.png')
plt.savefig(sine_plot_path, dpi=150)
plt.savefig('sine_wave_comparison.png', dpi=150)
plt.close()

# 2. Square Wave Voltage / Triangular Current Waveforms
I_p_peak_sq = V_s_peak / (4 * f * M_to_use)
V_p_peak_sq = (L_p / M_to_use) * V_s_peak

# Generate triangle wave current
t_norm = (t % T) / T
I_p_sq = np.zeros_like(t)
V_s_sq = np.zeros_like(t)
V_p_sq = np.zeros_like(t)

for i, tn in enumerate(t_norm):
    if tn < 0.5:
        I_p_sq[i] = -I_p_peak_sq + 4 * I_p_peak_sq * tn
        V_s_sq[i] = -V_s_peak
        V_p_sq[i] = -V_p_peak_sq
    else:
        I_p_sq[i] = 3 * I_p_peak_sq - 4 * I_p_peak_sq * tn
        V_s_sq[i] = V_s_peak
        V_p_sq[i] = V_p_peak_sq

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6), sharex=True)
ax1.plot(t * 1e6, I_p_sq, 'g-', label='Primary Current $I_p(t)$ (Triangular)')
ax1.set_ylabel('Primary Current (A)', color='g')
ax1.tick_params(axis='y', labelcolor='g')
ax1.grid(True)
ax1.set_title(f'Square Wave Voltage Drive at {f/1e3:.1f} kHz')

ax2.plot(t * 1e6, -V_s_sq, 'r-', label='Secondary Voltage $V_s(t)$ (Square)')
ax2.set_ylabel('Secondary Voltage (V)', color='r')
ax2.tick_params(axis='y', labelcolor='r')
ax2.set_xlabel('Time (us)')
ax2.grid(True)

plt.tight_layout()
square_plot_path = os.path.join(artifacts_dir, 'square_wave_comparison.png')
plt.savefig(square_plot_path, dpi=150)
plt.savefig('square_wave_comparison.png', dpi=150)
plt.close()

print("Waveform plots generated and saved successfully!")
print(f"Saved to artifacts directory: {artifacts_dir}")
"""

    # Populate cells
    nb['cells'] = [
        nbf.v4.new_markdown_cell(intro_md),
        nbf.v4.new_code_cell(constants_code),
        nbf.v4.new_markdown_cell(inductance_md),
        nbf.v4.new_code_cell(inductance_code),
        nbf.v4.new_code_cell(resistance_code),
        nbf.v4.new_markdown_cell(sine_md),
        nbf.v4.new_code_cell(sine_code),
        nbf.v4.new_markdown_cell(square_md),
        nbf.v4.new_code_cell(square_code),
        nbf.v4.new_code_cell(plot_code)
    ]

    with open('physics_calculation.ipynb', 'w') as f:
        nbf.write(nb, f)
    print("Jupyter Notebook created.")

if __name__ == '__main__':
    # Define standard artifacts path
    artifacts_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports")
    build_notebook(artifacts_dir)
