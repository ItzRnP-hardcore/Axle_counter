# Industrial DMA Axle Counter

This repository contains the complete software and physics simulation stack for an **Industrial DMA Axle Counter**. The system is designed to detect the passage of railway wheels using a set of air-core coils, overcoming the need for fragile ferrite cores while maintaining a high signal-to-noise ratio.

The project is divided into two primary, distinct components:
1. **`secondary_coil_sensor/`**: The ESP32-S3 firmware that actively monitors the coils and performs signal processing.
2. **`axlecounter_3dphysics/`**: The 3D magnetic physics simulations (via FEMM and Python) used to mathematically prove and optimize the sensor's design.

---

## Basic Working Principle

The axle counter operates on the principle of **electromagnetic coupling changes**:
1. **Transmission**: A primary coil is excited with specific frequency tones (e.g., 12.5 kHz and 17.5 kHz).
2. **Coupling**: The magnetic flux passes through the space above the track and induces a voltage in a secondary (receiver) coil.
3. **Wheel Dip**: When a massive ferromagnetic railway wheel passes over the coils, it disturbs the magnetic field. Due to eddy currents and magnetic shunting, the induced voltage in the secondary coil experiences a sharp "dip" (often over 90% drop in coupling).
4. **Detection**: An ESP32-S3 microcontroller continuously samples the secondary coil's voltage using its built-in ADC (via DMA). It applies a real-time Fast Fourier Transform (FFT) to isolate the specific frequencies, compares the magnitude against an auto-calibrated threshold, and registers an axle count when a dip is detected.

---

## Repository Structure & File Operations

### 1. `secondary_coil_sensor/` (Firmware)
This folder holds the ESP-IDF C codebase for the ESP32-S3 microcontroller. 
- **`main/main.c`**: The core application logic. It initializes the DMA ADC, runs the ESP-DSP complex FFT pipeline, handles Exponential Moving Average (EMA) smoothing for auto-calibration, and logs detected axle passes to an SD card.
- **`CMakeLists.txt` & `sdkconfig`**: Build configuration files for the ESP-IDF toolchain.
- **`docs/FIRMWARE_DOCS.md`**: Detailed technical explanation of the DSP pipeline, DMA buffer management, and calibration state machine.

### 2. `axlecounter_3dphysics/` (Physics & Simulation)
This folder contains Python scripts, Jupyter notebooks, and FEMM (Finite Element Method Magnetics) files used to optimize the coil geometries.
- **`config.py`**: The central configuration file holding the physical parameters (coil radius, depth, turns, frequency) used across all scripts.
- **`run_all.py` / `run_all.bat`**: Top-level orchestration scripts to execute the entire physics simulation pipeline automatically.
- **`simulation_and_femm/`**: 
  - `femm_run_once.py`: Runs a single instance of the FEMM magnetic simulation.
  - `femm_sweep.py`: Sweeps across multiple design parameters to find optimal flux linkages.
  - `femm_wheel_dip.py`: Simulates the magnetic field specifically when a steel wheel is present to calculate the detection dip percentage.
- **`optimization_and_design/`**:
  - `optimize_coils.py` & `optimize_air_core.py`: Solvers that use Design of Experiments (DOE) and Response Surface Methodology (RSM) to find the coil shape/tilt that yields the highest mutual inductance.
  - `calc_caps.py`: Calculates the required resonant tuning capacitors for the coils based on the FEMM-derived inductance.
- **`analysis_and_reporting/`**:
  - `physics_calculation.ipynb` & `sweep_analysis.ipynb`: Interactive Jupyter notebooks analyzing the simulation data and validating Faraday's Law and resonance identities.
  - `sanity_check.py`: An automated physics audit script that ensures all results obey the $N^2$ scaling laws and expected voltage formulas.
  - `build_report.py`: Rebuilds the full project report (`Axle_Counter_Full_Report.md` + `.pdf`) and `RUN_SUMMARY.md` entirely from live `config.py` and `reports/` data, so the report can never contradict the results.
  - `md_to_pdf.py`: Renders Markdown (including LaTeX display equations) to PDF.
- **`reports/`**: Every generated artefact — the report (`Axle_Counter_Full_Report.pdf`), `RUN_SUMMARY.md`, `sanity_check_report.md`, CSV datasets, JSON optimums, and plots in `figures/` illustrating mutual inductance, resonant voltage and flux maps.
- **`old_files/`**: Deprecated scripts, pre-refactor model backups, and superseded reports that no longer describe the current model.

---

## How to Operate Everything

### Running the ESP32 Firmware
1. **Prerequisites**: Install [ESP-IDF v5.x](https://docs.espressif.com/projects/esp-idf/en/latest/esp32/get-started/).
2. **Hardware**: Connect Sensor 1 to GPIO1, Sensor 2 to GPIO2, and a calibration button to GPIO35 on your ESP32-S3.
3. **Build and Flash**:
   Navigate into the sensor directory and build:
   ```bash
   cd secondary_coil_sensor
   idf.py set-target esp32s3
   idf.py build
   idf.py -p (YOUR_PORT) flash monitor
   ```

### Running the 3D Physics Simulations
1. **Prerequisites**: 
   - Install [FEMM 4.2](https://www.femm.info/wiki/Download).
   - Install Python 3 with the required packages: `pip install pyfemm numpy pandas matplotlib scipy jupyter`.
2. **Execute Full Pipeline**:
   You can generate all data, run the sweeps, and produce the reports by simply double-clicking `run_all.bat` or executing it from the terminal:
   ```bash
   cd axlecounter_3dphysics
   ./run_all.bat
   ```
3. **Manual Analysis**: 
   If you wish to explore the data interactively, start a Jupyter server in the `analysis_and_reporting/` directory and open `physics_calculation.ipynb`.
