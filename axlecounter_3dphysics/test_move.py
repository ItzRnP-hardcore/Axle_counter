import femm, config

def test():
    femm.openfemm()
    
    # 1. Open
    femm.opendocument(config.FEM_FILE)
    print("Opened base file.")
    
    # 2. Fix labels exactly like femm_sweep.py did
    # Fix labels AND move them to positions that were proven to work in femm_sweep!
    
    # RX Half 1
    femm.mi_selectlabel(61.6, 110.3)
    femm.mi_movetranslate(0, 0) # stay
    femm.mi_setblockprop("18 AWG", 1, 0, "New Circuit", 0, 2, 100)
    femm.mi_clearselected()
    
    # RX Half 2
    femm.mi_selectlabel(86.7, 106.9)
    femm.mi_movetranslate(81.68 - 86.7, 107.58 - 106.9)
    femm.mi_setblockprop("18 AWG", 1, 0, "New Circuit", 0, 2, -100)
    femm.mi_clearselected()
    
    # TX Half 1
    femm.mi_selectlabel(-89.1, 120.9)
    femm.mi_movetranslate(-84.1 - (-89.1), 121.52 - 120.9)
    femm.mi_setblockprop("18 AWG", 1, 0, "Receiver", 0, 1, -100)
    femm.mi_clearselected()
    
    # TX Half 2
    femm.mi_selectlabel(-64.1, 124.0)
    femm.mi_movetranslate(0, 0) # stay
    femm.mi_setblockprop("18 AWG", 1, 0, "Receiver", 0, 1, 100)
    femm.mi_clearselected()
    
    femm.mi_selectlabel(0, 120)
    femm.mi_setblockprop("1018 Steel", 1, 0, "<None>", 0, 0, 0)
    femm.mi_clearselected()
    
    femm.mi_selectlabel(-168, 198)
    femm.mi_setblockprop("Air", 1, 0, "<None>", 0, 0, 0)
    femm.mi_clearselected()
    
    try:
        femm.mi_analyze(1)
        print("Analyzed successfully after fixing labels (without moving)!")
    except Exception as e:
        print(f"Failed to analyze after fixing labels: {e}")
        
    # 3. Try to move it
    try:
        femm.mi_selectrectangle(-110, 90, -50, 150, 4)
        femm.mi_movetranslate(8, 0)
        print("Moved successfully!")
        
        femm.mi_saveas("moved.fem")
        print("Saved to moved.fem")
        
        femm.mi_analyze(1)
        print("Analyzed successfully after moving!")
    except Exception as e:
        print(f"Failed to analyze after moving: {e}")
        
    femm.closefemm()

if __name__ == "__main__":
    test()
