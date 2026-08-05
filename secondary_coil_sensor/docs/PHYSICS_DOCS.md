# 3D Physics Simulation Documentation

The `axlecounter_3dphysics` directory contains tools and models for simulating the electromagnetic fields of the axle counter coils. The primary goal is to ensure the strongest stable air-core coupling and to quantify the detection dip caused by a passing steel railway wheel.

## Physics Overview & Goals

- **No Ferrite Core**: The premise of this axle counter design is that the coils must stay air-core. A steel wheel is detected by the DIP it causes in coil coupling. Thus, the objective is to maximize air-only coupling to provide the best signal-to-noise ratio (SNR) for the detection dip.
- **Wheel Dip Confirmation**: Simulations confirm that dropping a steel wheel into the field causes mutual inductance to fall by over 90% (e.g., from 0.0371 µH to 0.0031 µH), reducing the RX voltage from ~11.6 mV to ~1.0 mV. This confirms a highly robust detection mechanism.

## Time-Harmonic (AC) vs Magnetostatic

A common pitfall is running simulations in a magnetostatic regime (Frequency = 0). For an axle counter excited at 10–20 kHz, a magnetostatic solve ignores:
1. Eddy currents induced in the steel rail (the dominant loss + phase-shift mechanism).
2. Skin effect in the copper wire.

The codebase automatically switches the simulation into an AC time-harmonic state using `femm_utils.set_frequency(config.FREQUENCY_HZ)` prior to analysis. This yields physically representative coupling and losses. A 20 kHz AC run reveals the true RX induced voltage and properly scales the mutual inductance.

## Key FEMM Scripts & Utilities

- `config.py`: Single source of truth for hardware parameters (Frequency, Drive Current, Circuit Names, Output Directory). 
- `femm_utils.py`: Shared helper module to handle FEMM operations (`open_base()`, `set_frequency()`, `extract_mutual_inductance()`).
- `femm_wheel_dip.py` (`run_wheel.bat`): A live FEMM run that introduces a steel wheel into the field to measure the detection dip.
- `femm_sweep.py` (`run_sweep.bat`): A script designed to vary block/circuit properties (like coil turns and drive current) without altering the base geometry. It creates a scratch file (`_sweep_work.fem`) to protect the base model.
- `optimize_air_core.py`: Evaluates and maximizes RX signal/flux linkage subject to buildable capacitor voltage ratings. It outputs design tables for various capacitor classes.

## Optimization Procedure

The coil geometry and number of turns directly affect the induced signal. The optimization scripts sweep parameters such as turns (`N = 50..200`) and calculate mutual inductance `M`. Under these simulations, `M` follows `N^2` and RX voltage scales linearly with turns and drive current, verifying physically correct behavior. Based on capacitor voltage limits (`V_rx/V_cap = M/L`), the recommended air-core build is ~119 turns, 70 mm, AWG16 wire, tuned to 25 kHz.
