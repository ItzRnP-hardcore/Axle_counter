"""Debug script: verify that block labels can be re-assigned and the coil
group moved without breaking the mesh/solve.

Fixed over the original:
  * Works on a scratch copy (the old version analyzed the base file in place,
    and FEMM's auto-save on analyze mutated it).
  * Assigns each label to the circuit/group it actually has in the saved file
    (the old version SWAPPED TX and RX -- that swap is how the base file ended
    up with "New Circuit" on the right-hand coil).
  * Uses the current label coordinates from config (the old hard-coded ones
    predate the geometry move and no longer select anything).
"""
import femm
import config
import femm_utils


def test():
    femm.openfemm()
    try:
        femm_utils.open_scratch("_test_move_work.fem", set_ac=False)
        print("Opened scratch copy of base file.")

        # Re-assert the block properties exactly as the file defines them.
        for (x, y, turns) in config.TX_LABELS:
            femm.mi_selectlabel(x, y)
            femm.mi_setblockprop(config.COIL_WIRE_BLOCK, 1, 0,
                                 config.TX_CIRCUIT, 0, config.TX_GROUP, turns)
            femm.mi_clearselected()
        for (x, y, turns) in config.RX_LABELS:
            femm.mi_selectlabel(x, y)
            femm.mi_setblockprop(config.COIL_WIRE_BLOCK, 1, 0,
                                 config.RX_CIRCUIT, 0, config.RX_GROUP, turns)
            femm.mi_clearselected()

        femm.mi_selectlabel(0, 120)
        femm.mi_setblockprop("1018 Steel", 1, 0, "<None>", 0, 0, 0)
        femm.mi_clearselected()
        femm.mi_selectlabel(-168, 198)
        femm.mi_setblockprop("Air", 1, 0, "<None>", 0, 0, 0)
        femm.mi_clearselected()

        try:
            femm.mi_analyze(1)
            print("Analyzed successfully after re-asserting labels!")
        except Exception as e:
            print(f"Failed to analyze after re-asserting labels: {e}")

        # Try moving the left (RX) coil as a group.
        try:
            femm.mi_clearselected()
            femm.mi_selectgroup(config.RX_GROUP)
            femm.mi_movetranslate(8, 0)
            print("Moved successfully!")
            femm.mi_saveas("_test_moved.fem")
            femm.mi_analyze(1)
            print("Analyzed successfully after moving!")
        except Exception as e:
            print(f"Failed to analyze after moving: {e}")
        femm.mi_close()
    finally:
        femm.closefemm()


if __name__ == "__main__":
    test()
