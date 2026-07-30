"""
Quantify the axle-counter DETECTION DIP with a live FEMM run.

Solves the coupling twice:
  (1) baseline  -- no wheel, open air between the coils
  (2) wheel present -- a steel block (the passing wheel/flange) is added into
      the field above the rail, shunting flux between the coils.
The drop in mutual inductance / RX flux is the detection signal.
Works on a SCRATCH copy so the base model is never modified.
"""
import os, json, traceback
import config

HERE=config.BASE_DIR
WORK=os.path.join(HERE,"_wheel_work.fem")
OUT=os.path.join(HERE,"reports","wheel_dip_result.txt")

# steel "wheel" cross-section (rectangle) placed above the rail head, in the
# coil-to-coil flux path (mm)
WX0,WX1,WY0,WY1 = -32, 32, 150, 250

def coil_flux(femm):
    femm.mi_analyze(1); femm.mi_loadsolution()
    rx=femm.mo_getcircuitproperties(config.RX_CIRCUIT)
    tx=femm.mo_getcircuitproperties(config.TX_CIRCUIT)
    M=(abs(rx[2])/abs(tx[0]))*1e6 if abs(tx[0])>0 else 0.0
    femm.mo_close()
    return M, abs(rx[2]), abs(rx[1])

with open(OUT,"w") as f:
    def log(m): print(m); f.write(m+"\n"); f.flush()
    try:
        import femm
        femm.openfemm()
        femm.opendocument(config.FEM_FILE)
        femm.mi_saveas(WORK)
        femm.mi_probdef(config.FREQUENCY_HZ,"millimeters","planar",1e-8,
                        config.COIL_DEPTH_MM,30,0)
        # baseline
        M0,flux0,v0=coil_flux(femm)
        log("=== AXLE COUNTER DETECTION DIP (FEMM) ===")
        log(f"[No wheel]   M={M0:.5f} uH  RXflux={flux0:.4e} Wb  RXvolt={v0:.5f} V")
        # add steel wheel rectangle (group 3)
        for (x,y) in [(WX0,WY0),(WX1,WY0),(WX1,WY1),(WX0,WY1)]:
            femm.mi_addnode(x,y)
        femm.mi_addsegment(WX0,WY0,WX1,WY0)
        femm.mi_addsegment(WX1,WY0,WX1,WY1)
        femm.mi_addsegment(WX1,WY1,WX0,WY1)
        femm.mi_addsegment(WX0,WY1,WX0,WY0)
        cx,cy=(WX0+WX1)/2.0,(WY0+WY1)/2.0
        femm.mi_addblocklabel(cx,cy)
        femm.mi_selectlabel(cx,cy)
        femm.mi_setblockprop("1018 Steel",1,0,"<None>",0,3,0)
        femm.mi_clearselected()
        M1,flux1,v1=coil_flux(femm)
        log(f"[Wheel in]   M={M1:.5f} uH  RXflux={flux1:.4e} Wb  RXvolt={v1:.5f} V")
        dip=(M0-M1)/M0*100 if M0>0 else 0
        log(f"--> Detection dip: {dip:.1f}%  (M {M0:.5f} -> {M1:.5f} uH)")
        femm.mi_close(); femm.closefemm()
        with open(os.path.join(HERE,"reports","wheel_dip.json"),"w") as jf:
            json.dump(dict(M_no_wheel_uH=M0,M_wheel_uH=M1,dip_pct=dip,
                RXv_no_wheel=v0,RXv_wheel=v1), jf, indent=2)
        log("DONE OK")
    except Exception as e:
        log("ERROR: "+str(e)); f.write(traceback.format_exc())
