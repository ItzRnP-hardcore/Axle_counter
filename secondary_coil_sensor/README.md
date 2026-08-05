# Industrial DMA Axle Counter - Fixed

This repository contains the firmware and physics simulation for an ESP32-S3 based Industrial DMA Axle Counter. The system uses continuous ADC sampling and complex-FFT (via ESP-DSP) to detect railway wheel passes based on a dip in electromagnetic coupling between two air-core coils.

## Features
- **Continuous DMA ADC**: Captures sensor data directly without CPU overhead.
- **ESP-DSP Complex FFT**: Utilizes single-pass interleaved Re/Im FFT for performant frequency domain analysis.
- **Auto-calibration & Smoothing**: Includes Exponential Moving Average (EMA) smoothing and automated threshold calibration for robust axle detection.
- **SD Card Logging**: Persists axle detection events and metrics.
- **Air-Core Coil Physics**: Co-designed with FEMM 3D physics simulation confirming high-SNR wheel dip without ferrite cores.

## Hardware Setup
- **Microcontroller**: ESP32-S3
- **Sensor 1 (12.5 kHz)**: GPIO1 (ADC1_CHANNEL_0)
- **Sensor 2 (17.5 kHz)**: GPIO2 (ADC1_CHANNEL_1)
- **Calibration Button**: GPIO 35

## Software Requirements
- ESP-IDF (v5.x recommended)
- FEMM 4.2 (for physics simulation only, optional for firmware build)

## Project Structure
- `main/`: Contains the ESP-IDF C codebase (`main.c` and helper files).
- `axlecounter_3dphysics/`: Contains FEMM and Python scripts for simulating coil magnetic fields and wheel interaction.
- `docs/`: Technical documentation detailing the firmware pipeline and physics simulation.

## Build and Flash
To build and flash the firmware onto the ESP32-S3:
```bash
idf.py set-target esp32s3
idf.py build
idf.py -p (PORT) flash monitor
```

## Documentation
- [Firmware Documentation](docs/FIRMWARE_DOCS.md)
- [3D Physics Simulation](docs/PHYSICS_DOCS.md)
