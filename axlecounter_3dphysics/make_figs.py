import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.tri as mtri

import os
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

nx,ny,na,tris=parse_ans(os.path.join(PROJ,"temp.ans"))
pts,segs,labels=parse_geom(os.path.join(PROJ,"temp.fem"))
print(f"Parsed FEM: {len(nx)} nodes, {len(tris)} tris, {len(pts)} pts, {len(segs)} segs")
triang=mtri.Triangulation(nx,ny,tris)
gcol={0:"#555555",1:ACCENT2,2:ACCENT3}

# A: flux map
fig,ax=plt.subplots(figsize=(8.2,7.4))
tcf=ax.tricontourf(triang,na*1e6,levels=40,cmap="RdBu_r")
ax.tricontour(triang,na*1e6,levels=26,colors="k",linewidths=0.45,alpha=0.55)
cb=fig.colorbar(tcf,ax=ax,shrink=0.85); cb.set_label(r"Vector potential $A_z$ ($\mu$Wb/m)")
for n0,n1,g in segs:
    x0,y0=pts[n0];x1,y1=pts[n1]; ax.plot([x0,x1],[y0,y1],color=gcol.get(g,"k"),lw=2.0)
ax.plot([],[],color=ACCENT2,lw=2,label="TX coil (grp 1)"); ax.plot([],[],color=ACCENT3,lw=2,label="RX coil (grp 2)")
ax.plot([],[],color="#555555",lw=2,label="Steel rail / boundary")
ax.set_xlim(-140,140); ax.set_ylim(-10,260); ax.set_aspect("equal")
ax.set_xlabel("x (mm)"); ax.set_ylabel("y (mm)")
ax.set_title("FEM Result - Magnetostatic Flux Map (2.5 A DC in TX)\nBlack contours = magnetic flux lines")
ax.legend(loc="upper right",framealpha=0.9)
fig.tight_layout(); fig.savefig(f"{FIGDIR}/01_fem_flux_map.png"); plt.close(fig)

# B: geometry
fig,ax=plt.subplots(figsize=(8.2,6.6))
for n0,n1,g in segs:
    x0,y0=pts[n0];x1,y1=pts[n1]; ax.plot([x0,x1],[y0,y1],color=gcol.get(g,"k"),lw=2.2)
for (lx,ly,mat,turns) in labels:
    ax.plot(lx,ly,"o",color="k",ms=4)
    c={2:"Air",3:"1018 Steel (rail)",4:f"coil N={turns:+d}"}.get(mat,str(mat))
    ax.annotate(c,(lx,ly),textcoords="offset points",xytext=(6,4),fontsize=8)
ax.set_xlim(-210,210); ax.set_ylim(-15,415); ax.set_aspect("equal")
ax.set_xlabel("x (mm)"); ax.set_ylabel("y (mm)")
ax.set_title("Model Geometry - Rail cross-section, TX/RX coils, air domain")
ax.plot([],[],color=ACCENT2,lw=2,label="TX coil"); ax.plot([],[],color=ACCENT3,lw=2,label="RX coil")
ax.plot([],[],color="#555555",lw=2,label="Rail + air boundary"); ax.legend(loc="upper right")
fig.tight_layout(); fig.savefig(f"{FIGDIR}/02_geometry.png"); plt.close(fig)

# analytical grid
mu0=4*np.pi*1e-7; rho=1.68e-8; f0=20000.0; omega=2*np.pi*f0
M0=0.00771e-6; Np0=100; Ns0=60; Ap0=0.01; As0=0.06; a=1.5e-3
def acr(rdc,a,fr):
    d=np.sqrt(rho/(np.pi*fr*mu0)); x=a/d
    return rdc*(1+x**4/48 if x<1 else x/2+0.75+3/(32*x))
turns=[50,100,150,200,300,400]; scales=[1.0,5.0,10.0,15.0,20.0]
M=np.zeros((len(turns),len(scales))); Vs=np.zeros_like(M)
for i,N in enumerate(turns):
    for j,sc in enumerate(scales):
        Ap=Ap0*sc; As=As0*sc; m=M0*(N/Np0)*(N/Ns0)*(Ap/Ap0)*(As/As0)
        M[i,j]=m*1e6; Vs[i,j]=2*omega*m*5.0

fig,ax=plt.subplots(figsize=(7.6,5.6))
im=ax.imshow(M,origin="lower",aspect="auto",cmap="viridis")
ax.set_xticks(range(len(scales))); ax.set_xticklabels([f"{s:g}x" for s in scales])
ax.set_yticks(range(len(turns))); ax.set_yticklabels(turns)
for i in range(len(turns)):
    for j in range(len(scales)):
        ax.text(j,i,f"{M[i,j]:.2f}",ha="center",va="center",
                color="white" if M[i,j]<M.max()*0.6 else "black",fontsize=8)
cb=fig.colorbar(im,ax=ax); cb.set_label(r"Mutual inductance $M$ ($\mu$H)")
ax.set_xlabel("Coil area scale factor"); ax.set_ylabel("Coil turns (Np=Ns)")
ax.set_title("Analytical Mutual Inductance vs Turns & Area"); ax.grid(False)
fig.tight_layout(); fig.savefig(f"{FIGDIR}/03_mutual_inductance.png"); plt.close(fig)

fig,ax=plt.subplots(figsize=(7.8,5.4))
for j,sc in enumerate(scales): ax.plot(turns,Vs[:,j],"o-",label=f"area {sc:g}x")
ax.axhline(3.3,color=ACCENT2,ls="--",lw=1.5,label="3.3 V target")
ax.set_xlabel("Coil turns (Np=Ns)"); ax.set_ylabel(r"$V_{s,pp}$ (V)")
ax.set_title("Induced Secondary Voltage @ 20 kHz, 5 A drive"); ax.legend()
fig.tight_layout(); fig.savefig(f"{FIGDIR}/04_secondary_voltage.png"); plt.close(fig)

csv=pd.read_csv(os.path.join(PROJ,"reports","axle_counter_sweep_data.csv"))
sub=csv[(csv.Frequency_Hz==20000)&(csv.Wire_Gauge_AWG==24)]
fig,ax=plt.subplots(figsize=(7.8,5.4))
for Np in sorted(sub.Primary_Turns_Np.unique()):
    s=sub[sub.Primary_Turns_Np==Np].sort_values("Flux_Loss_Pct")
    ax.plot(s.Flux_Loss_Pct,s.Peak_Current_A,"o-",ms=3,label=f"Np={Np}")
ax.set_yscale("log"); ax.set_xlabel("Flux loss (%)"); ax.set_ylabel("Peak current (A, log)")
ax.set_title("Required Primary Peak Current vs Flux Loss (20 kHz, AWG 24)")
ax.legend(title="Primary turns",ncol=2,fontsize=8)
fig.tight_layout(); fig.savefig(f"{FIGDIR}/05_current_vs_fluxloss.png"); plt.close(fig)

fig,ax=plt.subplots(figsize=(7.8,5.4))
for Np in sorted(sub.Primary_Turns_Np.unique()):
    s=sub[sub.Primary_Turns_Np==Np].sort_values("Flux_Loss_Pct")
    ax.plot(s.Flux_Loss_Pct,s.Resonant_Voltage_Peak_V,"o-",ms=3,label=f"Np={Np}")
ax.set_yscale("log"); ax.set_xlabel("Flux loss (%)"); ax.set_ylabel("Resonant drive V (peak, log)")
ax.set_title("Resonant Primary Drive Voltage vs Flux Loss (20 kHz, AWG 24)")
ax.legend(title="Primary turns",ncol=2,fontsize=8)
fig.tight_layout(); fig.savefig(f"{FIGDIR}/06_resonant_voltage.png"); plt.close(fig)

sub2=csv[(csv.Frequency_Hz==20000)&(csv.Primary_Turns_Np==160)&(csv.Wire_Gauge_AWG==24)].sort_values("Flux_Loss_Pct")
fig,ax=plt.subplots(figsize=(7.8,5.4))
ax.plot(sub2.Flux_Loss_Pct,sub2.Capacitor_Voltage_Peak_V,"o-",color=ACCENT,ms=4)
ax.axhline(250,color=ACCENT2,ls="--",lw=1.6,label="250 V procurement limit")
ax.fill_between(sub2.Flux_Loss_Pct,0,250,color=ACCENT3,alpha=0.12)
ax.set_yscale("log"); ax.set_xlabel("Flux loss (%)"); ax.set_ylabel("Cap peak voltage (V, log)")
ax.set_title("Capacitor Voltage Feasibility vs Flux Loss (20 kHz, Np=160)"); ax.legend()
fig.tight_layout(); fig.savefig(f"{FIGDIR}/07_capacitor_feasibility.png"); plt.close(fig)

flt=min(csv.Flux_Loss_Pct.unique(),key=lambda v:abs(v-99.0))
subg=csv[(csv.Frequency_Hz==20000)&(csv.Primary_Turns_Np==160)&(csv.Flux_Loss_Pct==flt)].sort_values("Wire_Gauge_AWG")
fig,ax=plt.subplots(figsize=(7.8,5.4))
ax.plot(subg.Wire_Gauge_AWG,subg.Resonant_Voltage_Peak_V,"o-",color=ACCENT,label="Resonant V")
ax.set_xlabel("Wire gauge (AWG - higher=thinner)"); ax.set_ylabel("Resonant drive V (peak)",color=ACCENT)
ax.tick_params(axis="y",labelcolor=ACCENT)
ax2=ax.twinx(); ax2.grid(False)
ax2.plot(subg.Wire_Gauge_AWG,subg.Peak_Current_A,"s--",color=ACCENT2,label="Peak current")
ax2.set_ylabel("Peak current (A)",color=ACCENT2); ax2.tick_params(axis="y",labelcolor=ACCENT2)
ax.set_title(f"Effect of Wire Gauge (20 kHz, Np=160, flux loss {flt:g}%)")
fig.tight_layout(); fig.savefig(f"{FIGDIR}/08_wire_gauge.png"); plt.close(fig)

freqs=[10,20]; ip=[7.66,3.83]; vpr=[22.41,13.89]; cap=[3.84,0.96]
x=np.arange(len(freqs))
fig,axs=plt.subplots(1,3,figsize=(11.5,4.0))
for ax,data,ttl,col,unit in zip(axs,[ip,vpr,cap],
    ["Required peak current","Resonant drive voltage","Resonant capacitor"],
    [ACCENT,ACCENT3,ACCENT2],["A","Vpp","nF"]):
    ax.bar(x,data,0.6,color=col)
    for xi,d in zip(x,data): ax.text(xi,d,f"{d:g} {unit}",ha="center",va="bottom",fontsize=9)
    ax.set_xticks(x); ax.set_xticklabels([f"{fq} kHz" for fq in freqs]); ax.set_title(ttl,fontsize=10); ax.margins(y=0.18)
fig.suptitle("Resonant-Matched Operating Point (M=3.43 uH, 3.3 Vpp target)")
fig.tight_layout(); fig.savefig(f"{FIGDIR}/09_operating_point.png"); plt.close(fig)
print("Figures:",sorted(os.listdir(FIGDIR)))
