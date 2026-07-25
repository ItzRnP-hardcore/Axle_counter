import femm
import csv
import os
import config

CSV_OUT = os.path.join(config.OUTPUT_DIR, "frequency_sweep_femm.csv")
WORK_FEM = os.path.join(config.BASE_DIR, "_freq_sweep_work.fem")

frequencies = [10000 + i * 500 for i in range(21)]

def run_freq_sweep():
    print(f"Starting frequency sweep from 10kHz to 20kHz... (Total {len(frequencies)} points)")
    femm.openfemm()
    results = []
    try:
        for freq in frequencies:
            print(f"Testing Frequency={freq} Hz ...")
            femm.opendocument(config.FEM_FILE)
            femm.mi_saveas(WORK_FEM)
            
            # Set the new frequency
            femm.mi_probdef(freq, "millimeters", "planar", 1e-8, 1, 30, 0)
            
            # Solve
            femm.mi_analyze(1)
            femm.mi_loadsolution()
            
            rx = femm.mo_getcircuitproperties("Receiver")
            tx = femm.mo_getcircuitproperties("New Circuit")
            
            rx_v = abs(rx[1])
            rx_flux = abs(rx[2])
            tx_i = abs(tx[0])
            
            M_uH = (rx_flux / tx_i) * 1e6 if tx_i > 0 else 0.0
            
            # Self-inductance of TX coil (assuming symmetric, L_rx is similar)
            tx_flux = abs(tx[2])
            L_tx_uH = (tx_flux / tx_i) * 1e6 if tx_i > 0 else 0.0
            
            results.append([freq, tx_i, rx_flux, M_uH, rx_v, L_tx_uH])
            
            femm.mo_close()
            femm.mi_close()
    except Exception as e:
        print(f"Error during frequency sweep: {e}")
        import traceback; traceback.print_exc()
    finally:
        femm.closefemm()

    with open(CSV_OUT, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Frequency_Hz", "TX_Current_A", "RX_Flux_Wb", "Mutual_Inductance_uH", "RX_Voltage_V", "L_TX_uH"])
        w.writerows(results)
    print(f"Sweep complete ({len(results)} runs). Data -> {CSV_OUT}")

if __name__ == "__main__":
    run_freq_sweep()
