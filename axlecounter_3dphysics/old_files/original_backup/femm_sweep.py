import femm
import csv
import os
import math
import config

ARTIFACTS_DIR = r"C:\Users\rudra\.gemini\antigravity-ide\brain\7f3c3b53-b0b9-4668-aaf9-350bbec75fbb"
CSV_OUT = os.path.join(ARTIFACTS_DIR, "coil_parameter_sweep.csv")

# Sweep parameters
turns_sweep = [50, 100, 150]
scale_sweep = [0.8, 1.0, 1.2]

def run_sweep():
    print("Starting FEMM Parameter Sweep...")
    femm.openfemm()
    
    results = []
    
    try:
        for turns in turns_sweep:
            for scale in scale_sweep:
                print(f"Testing Turns={turns}, Scale={scale}x...")
                
                femm.opendocument(config.FEM_FILE)
                
                # We need to change turns. 
                # In the base file, the coils are made of 4 block labels.
                # Group 1 (TX) labels: (-89.1, 120.9) and (-64.1, 124.0)
                # Group 2 (RX) labels: (61.6, 110.3) and (86.7, 106.9)
                # Note: "New Circuit" is Circuit 1, "Receiver" is Circuit 2
                
                # --- MODIFY TURNS ---
                # We'll just modify the circuits instead of the blocks, or modify the blocks directly.
                # Actually, the most robust way in FEMM is to select the label and setblockprop.
                # Let's set both sides of the coil to the new turns. 
                # Side 1 of TX
                femm.mi_selectlabel(-89.1, 120.9)
                femm.mi_setblockprop("18 AWG", 1, 0, "Receiver", 0, 1, -turns) # Based on original file properties
                femm.mi_clearselected()
                
                # Side 2 of TX
                femm.mi_selectlabel(-64.1, 124.0)
                femm.mi_setblockprop("18 AWG", 1, 0, "Receiver", 0, 1, turns)
                femm.mi_clearselected()
                
                # Side 1 of RX
                femm.mi_selectlabel(61.6, 110.3)
                femm.mi_setblockprop("18 AWG", 1, 0, "New Circuit", 0, 2, turns)
                femm.mi_clearselected()
                
                # Side 2 of RX
                femm.mi_selectlabel(86.7, 106.9)
                femm.mi_setblockprop("18 AWG", 1, 0, "New Circuit", 0, 2, -turns)
                femm.mi_clearselected()
                
                # --- MODIFY SCALE (AREA) ---
                if scale != 1.0:
                    # Scale TX (Group 1)
                    femm.mi_selectgroup(1)
                    femm.callfemm(f"mi_scale({config.TX_CENTER_X}, {config.TX_CENTER_Y}, {scale})")
                    femm.mi_clearselected()
                    
                    # Scale RX (Group 2)
                    femm.mi_selectgroup(2)
                    femm.callfemm(f"mi_scale({config.RX_CENTER_X}, {config.RX_CENTER_Y}, {scale})")
                    femm.mi_clearselected()
                
                # Analyze
                femm.mi_analyze(1)
                femm.mi_loadsolution()
                
                # Get circuit properties
                rx_props = femm.mo_getcircuitproperties('Receiver')
                tx_props = femm.mo_getcircuitproperties('New Circuit')
                
                rx_voltage = abs(rx_props[1])
                rx_flux = abs(rx_props[2])
                tx_current = abs(tx_props[0])
                
                M_uH = (rx_flux / tx_current) * 1e6 if tx_current > 0 else 0
                
                results.append([turns, scale, tx_current, rx_flux, M_uH, rx_voltage])
                
                femm.mo_close()
                femm.mi_close()
                
    except Exception as e:
        print(f"Error during sweep: {e}")
    finally:
        femm.closefemm()
        
    # Write to CSV
    with open(CSV_OUT, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Turns', 'Area_Scale_Factor', 'TX_Current_A', 'RX_Flux_Wb', 'Mutual_Inductance_uH', 'RX_Voltage_V'])
        writer.writerows(results)
        
    print(f"Sweep complete. Data saved to {CSV_OUT}")

if __name__ == "__main__":
    run_sweep()
