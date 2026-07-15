import femm
import config

femm.openfemm()
femm.opendocument(config.FEM_FILE)
femm.mi_analyze(1)
femm.mi_loadsolution()
# Get area of a block
# mo_blockintegral(5) gives the cross-section area of the selected block
femm.mo_selectblock(config.TX_CENTER_X - config.OPTIMAL_X, config.TX_CENTER_Y + config.OPTIMAL_Y)
area = femm.mo_blockintegral(5)
print(f"TX Area: {area} m^2")
femm.mo_close()
femm.mi_close()
femm.closefemm()
