import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.tri as mtri
from matplotlib.patches import Rectangle

PROJ = os.path.dirname(os.path.abspath(__file__))
FIGDIR = os.path.join(PROJ, "reports", "figures")
os.makedirs(FIGDIR, exist_ok=True)
plt.rcParams.update({"figure.dpi":130,"savefig.dpi":150,"font.size":11,"axes.grid":True,
    "grid.alpha":0.3,"axes.axisbelow":True,"figure.facecolor":"white","axes.facecolor":"white"})
ACCENT="#1f5fa8"; ACCENT2="#c0392b"; ACCENT3="#27ae60"

def parse_ans(path):
    with open(path) as f: lines=f.readlines()
    si=next(i for i,l in enumerate(lines) if l.strip().startswith("[Solution]"))
    n=int(lines[si+1]); nx=[];ny=[];na=[]
    idx=si+2
    for k in range(n):
        p=lines[idx+k].split(); nx.append(float(p[0]));ny.append(float(p[1]));na.append(float(p[2]))
    idx+=n; ne=int(lines[idx]); idx+=1; tris=[]
    for k in range(ne):
        p=lines[idx+k].split(); tris.append([int(p[0]),int(p[1]),int(p[2])])
    return np.array(nx),np.array(ny),np.array(na),np.array(tris)

def parse_geom(path):
    with open(path) as f: lines=[l.rstrip("\n") for l in f]
    def sec(tag):
        i=next(i for i,l in enumerate(lines) if l.strip().startswith(tag))
        n=int(lines[i].split("=")[1]); return [lines[i+1+k].split("\t") for k in range(n)]
    pts=[(float(r[0]),float(r[1])) for r in sec("[NumPoints]")]
    segs=[(int(r[0]),int(r[1]),int(r[5])) for r in sec("[NumSegments]")]
    labels=[(float(r[0]),float(r[1]),int(r[2]),int(r[7])) for r in sec("[NumBlockLabels]")]
    return pts,segs,labels

_fem=os.path.join(PROJ,"_wheel_work.fem"); _ans=os.path.join(PROJ,"_wheel_work.ans")
if not (os.path.exists(_fem) and os.path.exists(_ans)):
    raise SystemExit("_wheel_work.fem/.ans not found -- run femm_wheel_dip.py "
                     "(run_wheel.bat) first.")
nx,ny,na,tris=parse_ans(_ans)
pts,segs,labels=parse_geom(_fem)
print(f"Parsed FEM: {len(nx)} nodes, {len(tris)} tris, {len(pts)} pts, {len(segs)} segs")
triang=mtri.Triangulation(nx,ny,tris)
# group 1 = LEFT coil = RX ("Receiver"), group 2 = RIGHT coil = TX
# ("New Circuit") -- the old legend had this backwards.
gcol={0:"#555555",1:ACCENT3,2:ACCENT2,3:"#7f8c8d"}

fig,ax=plt.subplots(figsize=(8.2,7.4))
tcf=ax.tricontourf(triang,na*1e6,levels=40,cmap="RdBu_r")
ax.tricontour(triang,na*1e6,levels=26,colors="k",linewidths=0.45,alpha=0.55)
cb=fig.colorbar(tcf,ax=ax,shrink=0.85); cb.set_label(r"Vector potential $A_z$ ($\mu$Wb/m)")
for n0,n1,g in segs:
    x0,y0=pts[n0];x1,y1=pts[n1]; ax.plot([x0,x1],[y0,y1],color=gcol.get(g,"k"),lw=2.0)
ax.plot([],[],color=ACCENT2,lw=2,label="TX coil (grp 2, right)")
ax.plot([],[],color=ACCENT3,lw=2,label="RX coil (grp 1, left)")
ax.plot([],[],color="#555555",lw=2,label="Steel rail / boundary")

# Add the wheel rectangle overlay
WX0,WX1,WY0,WY1 = -32, 32, 150, 250
wheel_rect = Rectangle((WX0, WY0), WX1-WX0, WY1-WY0, linewidth=2, edgecolor='#e74c3c', facecolor='#c0392b', alpha=0.3, label="Train Wheel Flange (Steel)")
ax.add_patch(wheel_rect)

ax.set_xlim(-140,140); ax.set_ylim(-10,260); ax.set_aspect("equal")
ax.set_xlabel("x (mm)"); ax.set_ylabel("y (mm)")
ax.set_title("FEM Result - Flux Map with Train Wheel present\nBlack contours = magnetic flux lines")
ax.legend(loc="upper right",framealpha=0.9)
fig.tight_layout()
outpath = f"{FIGDIR}/11_flux_with_wheel.png"
fig.savefig(outpath)
print("Saved", outpath)
plt.close(fig)
