"""
Quantify the axle-counter DETECTION DIP with a live FEMM run.

Solves the coupling twice:
  (1) baseline  -- no wheel, open air between the coils
  (2) wheel present -- a steel block (the passing wheel/flange) is added into
      the field above the rail, shunting flux between the coils.
The drop in mutual inductance / RX flux is the detection signal.

Works on a SCRATCH copy (_wheel_work.fem): FEMM auto-saves the open document
when it analyzes, so solving the base .FEM directly would mutate the model.

Writes reports/wheel_dip_result.txt (human-readable log, also echoed to
stdout) and reports/wheel_dip.json (M with/without wheel, dip percentage and
the RX voltages).
"""
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import os, json, traceback
import config

# Paths come from config, NOT from this file's own directory: the scripts live
# in subfolders, so dirname(__file__) is not the project root.
HERE=config.BASE_DIR
WORK=os.path.join(HERE,"_wheel_work.fem")
OUT=os.path.join(config.OUTPUT_DIR,"wheel_dip_result.txt")

# Steel "wheel" cross-section (rectangle) placed above the rail head, in the
# coil-to-coil flux path (mm). The constants live in config so that
# generate_wheel_figure.py draws the rectangle at exactly the position that
# was actually solved here.
WX0,WX1,WY0,WY1 = (config.WHEEL_X0, config.WHEEL_X1,
                   config.WHEEL_Y0, config.WHEEL_Y1)

def coil_flux(femm):
    """Solve the current model and return (M_uH, rx_flux, rx_voltage)."""
    femm.mi_analyze(1); femm.mi_loadsolution()   # mesh+solve, then open result
    # mo_getcircuitproperties -> [current, voltage, flux_linkage]. TX is the
    # energised "New Circuit" (group 2, right/+x coil); RX is the open
    # "Receiver" sense winding (group 1, left/-x coil).
    rx=femm.mo_getcircuitproperties(config.RX_CIRCUIT)
    tx=femm.mo_getcircuitproperties(config.TX_CIRCUIT)
    # M = RX flux linkage per amp of TX current, in microhenries.
    M=(abs(rx[2])/abs(tx[0]))*1e6 if abs(tx[0])>0 else 0.0
    femm.mo_close()   # close the post-processor; the model stays open
    return M, abs(rx[2]), abs(rx[1])

with open(OUT,"w") as f:
    def log(m):
        """Print a line and mirror it into the report file."""
        print(m); f.write(m+"\n"); f.flush()
    try:
        import femm
        femm.openfemm()
        femm.opendocument(config.FEM_FILE)
        # Redirect to the scratch file before anything solves, so the base
        # model survives FEMM's auto-save-on-analyze.
        femm.mi_saveas(WORK)
        # mi_probdef(frequency, units, type, precision, depth, minangle,
        # acsolver). Frequency > 0 selects the time-harmonic solver; depth
        # must be the real coil axial length so absolute flux/M/voltage are
        # physical rather than per-mm. Frequency and depth come from config;
        # the precision (1e-8), minimum mesh angle (30) and acsolver (0) are
        # FEMM numerical settings, not physical parameters, so they stay local.
        femm.mi_probdef(config.FREQUENCY_HZ,"millimeters","planar",1e-8,
                        config.COIL_DEPTH_MM,30,0)
        # Reference solve: geometry as saved, nothing between the coils.
        M0,flux0,v0=coil_flux(femm)
        log("=== AXLE COUNTER DETECTION DIP (FEMM) ===")
        log(f"[No wheel]   M={M0:.5f} uH  RXflux={flux0:.4e} Wb  RXvolt={v0:.5f} V")
        # Build the steel wheel: four corner nodes, then the four sides that
        # join them into a closed rectangle FEMM can treat as a region.
        for (x,y) in [(WX0,WY0),(WX1,WY0),(WX1,WY1),(WX0,WY1)]:
            femm.mi_addnode(x,y)
        femm.mi_addsegment(WX0,WY0,WX1,WY0)
        femm.mi_addsegment(WX1,WY0,WX1,WY1)
        femm.mi_addsegment(WX1,WY1,WX0,WY1)
        femm.mi_addsegment(WX0,WY1,WX0,WY0)
        # A block label at the centre is what gives the enclosed region a
        # material. Without it FEMM cannot mesh the interior.
        cx,cy=(WX0+WX1)/2.0,(WY0+WY1)/2.0
        femm.mi_addblocklabel(cx,cy)
        femm.mi_selectlabel(cx,cy)
        # mi_setblockprop(material, automesh, meshsize, circuit, magdir,
        # group, turns): solid steel, auto mesh, no circuit (it is not a
        # winding), tagged with its own group so the wheel is separable from
        # the coils. Material and group come from config
        # (WHEEL_MATERIAL = "1018 Steel", WHEEL_GROUP = 3) so this solve and
        # generate_wheel_figure.py describe the same block.
        femm.mi_setblockprop(config.WHEEL_MATERIAL,1,0,"<None>",0,
                             config.WHEEL_GROUP,0)
        femm.mi_clearselected()
        # Re-solve with the wheel in the flux path.
        M1,flux1,v1=coil_flux(femm)
        log(f"[Wheel in]   M={M1:.5f} uH  RXflux={flux1:.4e} Wb  RXvolt={v1:.5f} V")
        # Detection signal: percentage drop in mutual inductance.
        dip=(M0-M1)/M0*100 if M0>0 else 0
        log(f"--> Detection dip: {dip:.1f}%  (M {M0:.5f} -> {M1:.5f} uH)")
        femm.mi_close(); femm.closefemm()
        # Machine-readable copy of the same numbers for downstream scripts.
        with open(os.path.join(config.OUTPUT_DIR,"wheel_dip.json"),"w") as jf:
            json.dump(dict(M_no_wheel_uH=M0,M_wheel_uH=M1,dip_pct=dip,
                RXv_no_wheel=v0,RXv_wheel=v1), jf, indent=2)
        log("DONE OK")
    except Exception as e:
        log("ERROR: "+str(e)); f.write(traceback.format_exc())
