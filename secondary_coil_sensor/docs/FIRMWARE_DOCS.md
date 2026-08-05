# Firmware Technical Documentation

## Signal Processing Pipeline

The axle counter relies on a robust DSP pipeline to process the incoming high-frequency sensor data and extract the wheel passing events.

### 1. DMA ADC Capture
The ESP32-S3 continuously samples both sensors using ADC continuous mode. Data is transferred via DMA into an 8-block buffer. The effective sampling rate per channel is 40kHz (`SAMPLING_FREQ = 80000`, split across two channels). 

### 2. Complex FFT via ESP-DSP
When a DMA block completes, the data is processed:
- **DC Offset Removal**: A static DC offset (-2048) is subtracted from each sample.
- **Interleaved Re/Im Windowing**: Samples are loaded directly into an aligned interleaved complex working buffer and Hann-windowed in place.
- **FFT Transformation**: The array is transformed using `dsps_fft2r_fc32` and `dsps_bit_rev_fc32`. This avoids data corruption and ensures accurate bin contents for frequency domain analysis.

### 3. Peak Detection (`get_peak_in_band`)
Instead of wide-band energy sums, the pipeline uses narrow peak-bin detection around the target frequencies (12.5 kHz for S1, 17.5 kHz for S2). This reduces noise bin accumulation (from ~68 bins down to ~10 bins). The output is normalized by the number of samples (`SAMPLES = 512`), ensuring the magnitude is amplitude-proportional and directly relates to true RMS amplitude.

### 4. EMA Smoothing
Exponential Moving Average (EMA) smoothing (`EMA_ALPHA = 0.25f`) is applied to both magnitude outputs. This effectively low-passes the signal and kills per-frame FFT jitter without introducing meaningful latency.

## Axle Detection Logic

Detection is based on the sudden drop (dip) in signal amplitude caused by a steel wheel entering the air-core field.
- **Arming**: When the signal amplitude returns above the `arm_threshold`, the sensor is armed.
- **Triggering**: When the amplitude drops below the `dip_threshold` and the sensor is armed, a wheel presence is registered.
The firmware counts sequential triggers across both sensors to calculate speed and track the total number of axles passing.

## Calibration Mechanism

The system features auto-calibration via GPIO 35. 
- **Idle State**: The system operates normally using fixed thresholds.
- **Active Calibration**: Pressing the calibration button once initiates measurement of the steady-state ambient signal. Passing a wheel records the maximum dip. Pressing the button again finalizes calibration, dynamically calculating the `arm_threshold` and `dip_threshold` based on the measured peak signal and observed minimums.

Global correction maps (`S1_CAL_MAP`, `S2_CAL_MAP`) are included to piecewise linearly map the measured ADC amplitude to the actual expected Vpp amplitude.
