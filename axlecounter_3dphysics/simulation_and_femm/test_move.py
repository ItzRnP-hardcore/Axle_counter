"""Debug script: verify that block labels can be re-assigned and that a coil
group can be translated without breaking the mesh or the solve.

It re-stamps every coil block label with the circuit/group/turns the saved
model already uses, solves, then translates the RX (left) coil group by 8 mm
and solves again. Progress is printed to stdout; nothing is written to
reports/.

All work happens on a scratch copy (_test_move_work.fem), because FEMM
auto-saves the open document when it analyzes -- solving the base .FEM
directly would silently mutate the model. Label coordinates, circuit names
and group numbers all come from config so they stay in step with the file.
"""
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import femm
import config
from simulation_and_femm import femm_utils


def test():
    femm.openfemm()   # launch the FEMM process this script drives
    try:
        # Scratch copy, magnetostatic (set_ac=False) -- this is a geometry
        # smoke test, not a physics run.
        femm_utils.open_scratch("_test_move_work.fem", set_ac=False)
        print("Opened scratch copy of base file.")

        # Re-assert the block properties exactly as the file defines them.
        # mi_setblockprop(material, automesh, meshsize, circuit, magdir,
        # group, turns) acts on the current selection, so each label is
        # selected, stamped, then cleared.
        # TX = "New Circuit" = group 2 = the RIGHT (+x) coil.
        for (x, y, turns) in config.TX_LABELS:
            femm.mi_selectlabel(x, y)
            femm.mi_setblockprop(config.COIL_WIRE_BLOCK, 1, 0,
                                 config.TX_CIRCUIT, 0, config.TX_GROUP, turns)
            femm.mi_clearselected()
        # RX = "Receiver" = group 1 = the LEFT (-x) coil.
        for (x, y, turns) in config.RX_LABELS:
            femm.mi_selectlabel(x, y)
            femm.mi_setblockprop(config.COIL_WIRE_BLOCK, 1, 0,
                                 config.RX_CIRCUIT, 0, config.RX_GROUP, turns)
            femm.mi_clearselected()

        # Non-winding regions: the steel rail and the surrounding air. Both
        # take no circuit, group 0 and no turns.
        # LOCAL LITERALS: the rail and air block-label coordinates, and their
        # material names, describe the BACKGROUND of the saved .FEM file, not
        # the coil design. config defines a material/group for the wheel block
        # (WHEEL_MATERIAL / WHEEL_GROUP) but nothing for the rail or the air
        # region, so these are read back from the model as-is rather than
        # invented here.
        femm.mi_selectlabel(0, 120)
        femm.mi_setblockprop("1018 Steel", 1, 0, "<None>", 0, 0, 0)
        femm.mi_clearselected()
        femm.mi_selectlabel(-168, 198)
        femm.mi_setblockprop("Air", 1, 0, "<None>", 0, 0, 0)
        femm.mi_clearselected()

        # Check 1: the model still meshes and solves after the re-stamp.
        try:
            femm.mi_analyze(1)
            print("Analyzed successfully after re-asserting labels!")
        except Exception as e:
            print(f"Failed to analyze after re-asserting labels: {e}")

        # Check 2: move the left (RX) coil as a whole and solve again.
        # mi_selectgroup picks up every entity tagged with that group number,
        # so one call grabs the entire coil. FEMM clears the selection after
        # every move/rotate/scale, so the group must be re-selected before
        # EACH such operation -- otherwise the operation silently does nothing.
        try:
            femm.mi_clearselected()
            femm.mi_selectgroup(config.RX_GROUP)
            # LOCAL LITERAL: 8 mm is an arbitrary nudge to prove the move +
            # re-mesh path works. It is NOT a DOE point -- config.distance_shifts
            # is the real geometry grid, and axle.py owns that study -- so it is
            # deliberately not wired to config.
            femm.mi_movetranslate(8, 0)   # shift 8 mm in +x, 0 mm in y
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
