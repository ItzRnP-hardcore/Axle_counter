import femm
import os
import config

FEM_FILE = config.FEM_FILE
# We will overwrite the base file as the user requested
OUT_FILE = FEM_FILE

TX_CENTER_X, TX_CENTER_Y = config.TX_CENTER_X, config.TX_CENTER_Y
RX_CENTER_X, RX_CENTER_Y = config.RX_CENTER_X, config.RX_CENTER_Y

# Optimal values from grid search
dx = config.OPTIMAL_X
dy = config.OPTIMAL_Y
dtheta = config.OPTIMAL_THETA

SCALE_FACTOR = 1.5 # 1.5x size to maximize area without hitting the rail

def main():
    print("Opening FEMM...")
    femm.openfemm()
    try:
        femm.opendocument(FEM_FILE)
        
        # 1. MOVE & SCALE TRANSMITTER
        print("Applying optimal translation, rotation, and 1.5x scaling to TX...")
        femm.mi_clearselected()
        femm.mi_selectgroup(1) # TX is group 1
        
        # Translate
        femm.mi_movetranslate(-dx, dy)
        new_tx_cx = TX_CENTER_X - dx
        new_tx_cy = TX_CENTER_Y + dy
        
        # Rotate
        femm.mi_moverotate(new_tx_cx, new_tx_cy, dtheta)
        
        # Scale by 1.5x around new center using raw LUA to avoid pyfemm comma bug
        femm.callfemm(f'mi_scale({new_tx_cx}, {new_tx_cy}, {SCALE_FACTOR})')
        
        
        # 2. MOVE & SCALE RECEIVER
        print("Applying optimal translation, rotation, and 1.5x scaling to RX...")
        femm.mi_clearselected()
        femm.mi_selectgroup(2) # RX is group 2
        
        # Translate
        femm.mi_movetranslate(dx, dy)
        new_rx_cx = RX_CENTER_X + dx
        new_rx_cy = RX_CENTER_Y + dy
        
        # Rotate
        femm.mi_moverotate(new_rx_cx, new_rx_cy, -dtheta)
        
        # Scale by 1.5x around new center
        femm.callfemm(f'mi_scale({new_rx_cx}, {new_rx_cy}, {SCALE_FACTOR})')
        
        
        # 3. SAVE THE NEW FILE
        femm.mi_saveas(OUT_FILE)
        print(f"Geometry permanently updated and saved to: {OUT_FILE}")
        
        # 4. RUN BASELINE ANALYSIS FOR NEW GEOMETRY
        print("Running FEMM analysis to extract exact new Mutual Inductance...")
        femm.mi_analyze(1)
        femm.mi_loadsolution()
        
        rx_props = femm.mo_getcircuitproperties('Receiver')
        tx_props = femm.mo_getcircuitproperties('New Circuit')
        
        rx_flux = abs(rx_props[2])
        tx_current = abs(tx_props[0])
        
        new_M_uH = (rx_flux / tx_current) * 1e6 if tx_current > 0 else 0
        
        print(f"Exact Mutual Inductance extracted from FEMM: {new_M_uH:.6f} uH")
        
        # Append to config.py for the next scripts to use
        with open('config.py', 'a') as f:
            f.write(f"\n# New Geometry Base M from FEMM (Scale {SCALE_FACTOR}x)\n")
            f.write(f"SCALED_M_uH = {new_M_uH}\n")
            f.write(f"SCALED_FACTOR = {SCALE_FACTOR}\n")
            
        femm.mo_close()
        femm.mi_close()
        print("Done!")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        femm.closefemm()

if __name__ == '__main__':
    main()
