import femm
import numpy as np
import os

import config

# --- CONFIGURATION ---
FEM_FILE = config.FEM_FILE
TX_CENTER_X, TX_CENTER_Y = config.TX_CENTER_X, config.TX_CENTER_Y
RX_CENTER_X, RX_CENTER_Y = config.RX_CENTER_X, config.RX_CENTER_Y

# Design of Experiments (DOE) Grid
distance_shifts = config.distance_shifts
height_shifts = config.height_shifts
tilt_angles = config.tilt_angles


def run_experiment(dx, dy, dtheta):
    """
    Modifies the FEMM geometry, runs the solver, and returns the induced voltage.
    """
    print(f"Running simulation: ShiftX={dx}mm, ShiftY={dy}mm, Angle={dtheta}deg...")
    
    # Open the base file
    femm.opendocument(FEM_FILE)
    
    # -- MOVE TRANSMITTER --
    femm.mi_clearselected()
    femm.mi_selectgroup(1)
    # Move horizontally (dx) and vertically (dy)
    femm.mi_movetranslate(-dx, dy)
    # Rotate around its NEW shifted center
    femm.mi_moverotate(TX_CENTER_X - dx, TX_CENTER_Y + dy, dtheta)
    
    # -- MOVE RECEIVER --
    femm.mi_clearselected()
    femm.mi_selectgroup(2)
    # Move horizontally (dx) and vertically (dy)
    femm.mi_movetranslate(dx, dy)
    # Rotate around its NEW shifted center (opposite tilt for symmetry)
    femm.mi_moverotate(RX_CENTER_X + dx, RX_CENTER_Y + dy, -dtheta)
    
    femm.mi_saveas("temp.fem")
    femm.mi_analyze(1)  # 1 = minimize window during solve
    femm.mi_loadsolution()
    
    # Extract properties from both the Receiver and Transmitter circuits
    # mo_getcircuitproperties returns: [current, volts, flux_linkage]
    rx_props = femm.mo_getcircuitproperties('Receiver')
    tx_props = femm.mo_getcircuitproperties('New Circuit') # This is the Tx circuit name in your file
    
    rx_voltage_mag = abs(rx_props[1])
    rx_flux_mag = abs(rx_props[2]) # Flux linkage in Webers
    tx_current_mag = abs(tx_props[0]) # This will pull your 2.5A
    
    # Calculate Mutual Inductance (M = Flux Linkage / Tx Current)
    # Convert to microHenries (uH) for easier reading
    mutual_inductance_uH = (rx_flux_mag / tx_current_mag) * 1e6 if tx_current_mag > 0 else 0
    
    print(f"   -> Rx Voltage: {rx_voltage_mag:.4f} V | Rx Flux: {rx_flux_mag:.4e} Wb | Mutual Inductance: {mutual_inductance_uH:.4f} uH")
    
    # Close the documents so we can loop cleanly
    femm.mo_close()
    femm.mi_close()
    
    return mutual_inductance_uH

def main():
    print("Starting Automated RSM Optimization...")
    femm.openfemm()
    
    try:
        X_matrix_data = []
        Y_results = []
        
        # 1. Run the 27 Full Factorial Experiments (3x3x3)
        for dx in distance_shifts:
            for dy in height_shifts:
                for dtheta in tilt_angles:
                    v_out = run_experiment(dx, dy, dtheta)
                    Y_results.append(v_out)
                    
                    # Build the row for our matrix: [1, x, y, theta, x^2, y^2, theta^2]
                    X_matrix_data.append([1, dx, dy, dtheta, dx**2, dy**2, dtheta**2])
                
        # 2. Perform the Matrix Calculus (Least Squares Estimator)
        # Formula: b = (X'X)^-1 X' Y
        print("\n--- Solving Response Surface Matrix ---")
        X = np.array(X_matrix_data)
        Y = np.array(Y_results)
        
        # numpy's lstsq is a highly optimized way to do (X'X)^-1 X' Y
        coefficients, residuals, rank, s = np.linalg.lstsq(X, Y, rcond=None)
        b0, b1, b2, b3, b4, b5, b6 = coefficients
        
        print("\nRSM Equation Generated (Optimizing Mutual Inductance):")
        print(f"M (uH) = {b0:.4f} + ({b1:.4f} * X) + ({b2:.4f} * Y) + ({b3:.4f} * Theta) + ({b4:.4f} * X^2) + ({b5:.4f} * Y^2) + ({b6:.4f} * Theta^2)")
        
        # 3. Find the Optimum using Calculus (Setting derivative to 0)
        # dM/dx = b1 + 2*b4*x = 0  => x = -b1 / (2*b4)
        # dM/dy = b2 + 2*b5*y = 0  => y = -b2 / (2*b5)
        # dM/dTheta = b3 + 2*b6*theta = 0 => theta = -b3 / (2*b6)
        
        optimal_x = -b1 / (2 * b4) if b4 != 0 else 0
        optimal_y = -b2 / (2 * b5) if b5 != 0 else 0
        optimal_theta = -b3 / (2 * b6) if b6 != 0 else 0
        
        print("\n=== OPTIMAL CONFIGURATION ===")
        print(f"Ideal Distance Shift (X): {optimal_x:.2f} mm")
        print(f"Ideal Height Shift (Y): {optimal_y:.2f} mm")
        print(f"Ideal Tilt Angle (Theta): {optimal_theta:.2f} degrees")
        
        # --- NEW: Show the final result in FEMM ---
        print("\nApplying optimal configuration in FEMM so you can see it...")
        femm.opendocument(FEM_FILE)
        
        # Move Transmitter to optimal
        femm.mi_clearselected()
        femm.mi_selectgroup(1)
        femm.mi_movetranslate(-optimal_x, optimal_y)
        femm.mi_moverotate(TX_CENTER_X - optimal_x, TX_CENTER_Y + optimal_y, optimal_theta)
        
        # Move Receiver to optimal
        femm.mi_clearselected()
        femm.mi_selectgroup(2)
        femm.mi_movetranslate(optimal_x, optimal_y)
        femm.mi_moverotate(RX_CENTER_X + optimal_x, RX_CENTER_Y + optimal_y, -optimal_theta)
        
        # Run and show solution
        femm.mi_saveas("temp.fem")
        femm.mi_analyze(1) 
        femm.mi_loadsolution()
        
        rx_props = femm.mo_getcircuitproperties('Receiver')
        tx_props = femm.mo_getcircuitproperties('New Circuit')
        rx_flux = abs(rx_props[2])
        tx_current = abs(tx_props[0])
        optimal_M = (rx_flux / tx_current) * 1e6 if tx_current > 0 else 0
        
        print(f"Optimal Mutual Inductance extracted: {optimal_M:.4f} uH")
        
        # Append to config.py
        with open('config.py', 'a') as f:
            f.write(f"\n# Automatically added by axle.py\n")
            f.write(f"OPTIMAL_M_uH = {optimal_M}\n")
            f.write(f"OPTIMAL_X = {optimal_x}\n")
            f.write(f"OPTIMAL_Y = {optimal_y}\n")
            f.write(f"OPTIMAL_THETA = {optimal_theta}\n")
            
        print("Done! Optimal values saved to config.py.")
        femm.mo_close()
        femm.mi_close()
        
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        femm.closefemm()

if __name__ == "__main__":
    main()