"""Build the report figure set into reports/figures/.

Figures produced:
  01 FEM flux map        -- vector-potential field of a solved FEMM model
  02 Model geometry      -- rail cross-section, TX/RX coils, air domain
  03 Mutual inductance   -- analytic M vs turns and coil-area scale
  04 Secondary voltage   -- induced Vs,pp vs turns for each area scale
  05 Peak current        -- primary current needed vs flux loss
  06 Resonant voltage    -- resonant drive voltage vs flux loss
  07 Capacitor feasibility -- cap peak voltage vs flux loss, 250 V limit
  08 Wire gauge          -- drive voltage and current vs AWG
  09 Operating point     -- current / drive voltage / capacitor at 10 & 20 kHz

Figures 01-02 need a solved FEMM pair and are skipped if none is available.
Figures 05-08 come from the legacy sweep CSV and are skipped if it is missing.
"""
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.tri as mtri

import config

# Project root and output locations come from config -- this script lives in
# a subfolder, so dirname(__file__) is NOT the project root. Figures go to
# reports/figures/ under the configured output directory.
PROJ = config.BASE_DIR
FIGDIR = os.path.join(config.OUTPUT_DIR, "figures")
os.makedirs(FIGDIR, exist_ok=True)
plt.rcParams.update({"figure.dpi":130,"savefig.dpi":150,"font.size":11,"axes.grid":True,
    "grid.alpha":0.3,"axes.axisbelow":True,"figure.facecolor":"white","axes.facecolor":"white"})
ACCENT="#1f5fa8"; ACCENT2="#c0392b"; ACCENT3="#27ae60"

def parse_ans(path):
    """Read a solved FEMM .ans file: mesh nodes and the vector potential.

    The [Solution] block lists, for each mesh node, its x/y coordinate and the
    magnetic vector potential Az at that point, followed by the triangle list
    that connects the nodes into a mesh. Contours of constant Az are magnetic
    flux lines, so plotting Az shows the field pattern directly.

    Returns (x, y, Az, triangles) as numpy arrays.
    """
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
    """Read the drawn geometry out of a FEMM .fem input file.

    Pulls three tab-separated tables, each preceded by a "[NumX] = n" count:
      [NumPoints]      -- (x, y) coordinates of the outline nodes
      [NumSegments]    -- (start point, end point, group) straight edges; the
                          group number is what distinguishes rail from TX coil
                          from RX coil when colouring the plot
      [NumBlockLabels] -- (x, y, material index, circuit turns) markers that
                          assign a material and winding to each closed region

    Returns (points, segments, labels).
    """
    with open(path) as f: lines=[l.rstrip("\n") for l in f]
    def sec(tag):
        i=next(i for i,l in enumerate(lines) if l.strip().startswith(tag))
        n=int(lines[i].split("=")[1]); return [lines[i+1+k].split("\t") for k in range(n)]
    pts=[(float(r[0]),float(r[1])) for r in sec("[NumPoints]")]
    segs=[(int(r[0]),int(r[1]),int(r[5])) for r in sec("[NumSegments]")]
    labels=[(float(r[0]),float(r[1]),int(r[2]),int(r[7])) for r in sec("[NumBlockLabels]")]
    return pts,segs,labels

# Pick a geometry/solution pair for figures 01-02.
#
# A .fem and .ans are only a valid PAIR if the solution was produced FROM that
# geometry, i.e. the .ans is at least as new as the .fem. This matters: axle.py
# re-saves temp.fem on every DOE point, and when the final verification solve is
# infeasible the .fem is left holding a geometry that was never solved, while
# temp.ans still holds the previous point's field. Blindly pairing them draws
# one configuration's coil outline on top of another's flux map.
#
# Candidates in order of preference:
#   _live_tmp.*  -- base geometry, freshly solved by femm_run_once.py (best)
#   temp.*       -- DOE scratch from axle.py
#   base .FEM    -- shipped model + whatever .ans happens to sit beside it
_candidates = [
    (os.path.join(PROJ, "_live_tmp.fem"), os.path.join(PROJ, "_live_tmp.ans"),
     "base geometry (live solve)"),
    (os.path.join(PROJ, "temp.fem"), os.path.join(PROJ, "temp.ans"),
     "DOE scratch geometry"),
    (config.FEM_FILE, os.path.splitext(config.FEM_FILE)[0] + ".ans",
     "shipped base model"),
]


def _is_matched(fem, ans):
    """True if both exist and the solution is not older than the geometry."""
    if not (os.path.exists(fem) and os.path.exists(ans)):
        return False
    return os.path.getmtime(ans) >= os.path.getmtime(fem)


fem_pair, fem_src = None, None
for _f, _a, _desc in _candidates:
    if _is_matched(_f, _a):
        fem_pair, fem_src = (_f, _a), _desc
        break
    if os.path.exists(_f) and os.path.exists(_a):
        print(f"  (skipping {os.path.basename(_f)}: .ans is older than .fem -- "
              "stale pair, the solution does not belong to this geometry)")

# Segment group -> colour. In the saved model, group 1 is the LEFT coil = RX
# ("Receiver") and group 2 is the RIGHT coil = TX ("New Circuit"); group 0 is
# the rail and outer boundary. The legends below must follow this mapping.
# Group numbers come from config (RX_GROUP / TX_GROUP); group 0 has no config
# name because it is FEMM's default "ungrouped" bucket, not a coil.
gcol={0:"#555555",config.RX_GROUP:ACCENT3,config.TX_GROUP:ACCENT2}

if fem_pair:
    fem_f, ans_f = fem_pair
    nx,ny,na,tris=parse_ans(ans_f)
    pts,segs,labels=parse_geom(fem_f)
    print(f"Parsed FEM ({os.path.basename(fem_f)} = {fem_src}): {len(nx)} nodes, "
          f"{len(tris)} tris, {len(pts)} pts, {len(segs)} segs")
    triang=mtri.Triangulation(nx,ny,tris)

    # Figure 01 -- flux map. Filled colour is the vector potential Az
    # (uWb/m); the overlaid black contours are lines of constant Az, which
    # are the magnetic flux lines. The geometry edges are drawn on top.
    fig,ax=plt.subplots(figsize=(8.2,7.4))
    tcf=ax.tricontourf(triang,na*1e6,levels=40,cmap="RdBu_r")
    ax.tricontour(triang,na*1e6,levels=26,colors="k",linewidths=0.45,alpha=0.55)
    cb=fig.colorbar(tcf,ax=ax,shrink=0.85); cb.set_label(r"Vector potential $A_z$ ($\mu$Wb/m)")
    for n0,n1,g in segs:
        x0,y0=pts[n0];x1,y1=pts[n1]; ax.plot([x0,x1],[y0,y1],color=gcol.get(g,"k"),lw=2.0)
    ax.plot([],[],color=ACCENT2,lw=2,label=f"TX coil (grp {config.TX_GROUP}, right)")
    ax.plot([],[],color=ACCENT3,lw=2,label=f"RX coil (grp {config.RX_GROUP}, left)")
    ax.plot([],[],color="#555555",lw=2,label="Steel rail / boundary")
    ax.set_xlim(-140,140); ax.set_ylim(-10,260); ax.set_aspect("equal")
    ax.set_xlabel("x (mm)"); ax.set_ylabel("y (mm)")
    ax.set_title(f"FEM Result - Flux Map ({config.TX_CURRENT_MAG:g} A in TX, "
                 f"{config.FREQUENCY_HZ/1e3:.0f} kHz)\n{fem_src} -- "
                 "black contours = magnetic flux lines")
    ax.legend(loc="upper right",framealpha=0.9)
    fig.tight_layout(); fig.savefig(f"{FIGDIR}/01_fem_flux_map.png"); plt.close(fig)

    # Figure 02 -- geometry only, no field. Each block label is annotated
    # with its material (air / 1018 steel rail / coil) and, for coils, the
    # signed turn count, whose sign gives the winding direction.
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
    ax.plot([],[],color=ACCENT2,lw=2,label="TX coil (right)")
    ax.plot([],[],color=ACCENT3,lw=2,label="RX coil (left)")
    ax.plot([],[],color="#555555",lw=2,label="Rail + air boundary"); ax.legend(loc="upper right")
    fig.tight_layout(); fig.savefig(f"{FIGDIR}/02_geometry.png"); plt.close(fig)
else:
    print("No MATCHED solved FEM pair found (_live_tmp.*, temp.*, base .FEM/.ans) "
          "-- skipping figures 01/02. Run simulation_and_femm/femm_run_once.py "
          "to produce a freshly-solved base pair.")

# Analytical grid for figures 03-04, anchored to the VERIFIED FEMM baseline
# (config.M0_UH measured at BASELINE_TURNS on both coils). M ~ N^2 is
# FEMM-verified; the linear-in-area term is an analytic EXTRAPOLATION, so the
# large area scale factors below are order-of-magnitude guidance only.
# Constants, operating point and the 18 AWG wire radius all come from config.
mu0=config.MU0; rho=config.RHO_COPPER; f0=config.FREQUENCY_HZ; omega=config.OMEGA
M0=config.M0_H; N0=config.BASELINE_TURNS; a=config.WIRE_RADIUS_M
def acr(rdc,a,fr):
    """Scale a DC wire resistance up for the skin effect at frequency fr.

    d is the skin depth -- at AC the current crowds into a surface layer of
    roughly this thickness, shrinking the effective conducting area. Below
    a = d the correction is negligible; above it R grows about linearly.
    """
    d=np.sqrt(rho/(np.pi*fr*mu0)); x=a/d
    return rdc*(1+x**4/48 if x<1 else x/2+0.75+3/(32*x))
# Same sweep grids as the analytic CSV and the FEMM sweep -- from config.
turns=config.TURNS_SWEEP; scales=config.AREA_SCALE_SWEEP
M=np.zeros((len(turns),len(scales))); Vs=np.zeros_like(M)
for i,N in enumerate(turns):
    for j,sc in enumerate(scales):
        # Scale the anchor by N^2 and by the area factor on each coil.
        m=M0*(N/N0)**2*sc*sc
        # Faraday: peak induced voltage = omega * M * I, here at the configured
        # drive-current ceiling; the factor 2 converts peak to peak-to-peak.
        M[i,j]=m*1e6; Vs[i,j]=2*omega*m*config.MAX_DRIVE_CURRENT_A

# Figure 03 -- M over the turns x area grid, printed in each heatmap cell.
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

# Figure 04 -- the same grid as induced secondary voltage, one curve per area
# scale, against the configured signal target (config.DESIGN_TARGET_VPP).
fig,ax=plt.subplots(figsize=(7.8,5.4))
for j,sc in enumerate(scales): ax.plot(turns,Vs[:,j],"o-",label=f"area {sc:g}x")
ax.axhline(config.DESIGN_TARGET_VPP,color=ACCENT2,ls="--",lw=1.5,
           label=f"{config.DESIGN_TARGET_VPP:g} V target")
ax.set_xlabel("Coil turns (Np=Ns)"); ax.set_ylabel(r"$V_{s,pp}$ (V)")
ax.set_title(f"Induced Secondary Voltage @ {f0/1e3:.0f} kHz, "
             f"{config.MAX_DRIVE_CURRENT_A:g} A drive"); ax.legend()
fig.tight_layout(); fig.savefig(f"{FIGDIR}/04_secondary_voltage.png"); plt.close(fig)

# Figures 05-08 replot the legacy notebook parameter sweep. "Flux loss" is
# the assumed percentage of primary flux that never reaches the receiver, so
# higher flux loss demands more primary current for the same signal.
legacy_csv=os.path.join(config.OUTPUT_DIR,"axle_counter_sweep_data.csv")
if not os.path.exists(legacy_csv):
    raise SystemExit("Figures 01-04 written. reports/axle_counter_sweep_data.csv "
                     "is missing, skipping figures 05-09.")
csv=pd.read_csv(legacy_csv)
# NOTE ON THE SLICE VALUES BELOW: the frequency comes from config, but the
# AWG 24 and Np=160 filters are kept as local literals ON PURPOSE. This legacy
# CSV was generated on its own grid (AWG 20/24/28/34, Np 100/160/200); it does
# not contain the canonical 18 AWG or config.DESIGN_TURNS rows, so substituting
# config values here would select an empty slice and the figures would fail.
# Fig 05 -- hold frequency and wire gauge fixed, one curve per primary turn
# count: how much peak current the primary needs as flux loss worsens.
sub=csv[(csv.Frequency_Hz==config.FREQUENCY_HZ)&(csv.Wire_Gauge_AWG==24)]
fig,ax=plt.subplots(figsize=(7.8,5.4))
for Np in sorted(sub.Primary_Turns_Np.unique()):
    s=sub[sub.Primary_Turns_Np==Np].sort_values("Flux_Loss_Pct")
    ax.plot(s.Flux_Loss_Pct,s.Peak_Current_A,"o-",ms=3,label=f"Np={Np}")
ax.set_yscale("log"); ax.set_xlabel("Flux loss (%)"); ax.set_ylabel("Peak current (A, log)")
ax.set_title(f"Required Primary Peak Current vs Flux Loss ({f0/1e3:.0f} kHz, AWG 24)")
ax.legend(title="Primary turns",ncol=2,fontsize=8)
fig.tight_layout(); fig.savefig(f"{FIGDIR}/05_current_vs_fluxloss.png"); plt.close(fig)

# Fig 06 -- same slice, but the drive voltage the resonant primary needs.
fig,ax=plt.subplots(figsize=(7.8,5.4))
for Np in sorted(sub.Primary_Turns_Np.unique()):
    s=sub[sub.Primary_Turns_Np==Np].sort_values("Flux_Loss_Pct")
    ax.plot(s.Flux_Loss_Pct,s.Resonant_Voltage_Peak_V,"o-",ms=3,label=f"Np={Np}")
ax.set_yscale("log"); ax.set_xlabel("Flux loss (%)"); ax.set_ylabel("Resonant drive V (peak, log)")
ax.set_title(f"Resonant Primary Drive Voltage vs Flux Loss ({f0/1e3:.0f} kHz, AWG 24)")
ax.legend(title="Primary turns",ncol=2,fontsize=8)
fig.tight_layout(); fig.savefig(f"{FIGDIR}/06_resonant_voltage.png"); plt.close(fig)

# Fig 07 -- the series resonant capacitor sees a large voltage (I/(w*C)).
# The shaded band is the region that stays under the lowest standard film-cap
# class (config.CAP_VOLTAGE_CLASSES[0] = 250 V), the procurement limit here.
cap_limit_v=config.CAP_VOLTAGE_CLASSES[0]
sub2=csv[(csv.Frequency_Hz==config.FREQUENCY_HZ)&(csv.Primary_Turns_Np==160)&(csv.Wire_Gauge_AWG==24)].sort_values("Flux_Loss_Pct")
fig,ax=plt.subplots(figsize=(7.8,5.4))
ax.plot(sub2.Flux_Loss_Pct,sub2.Capacitor_Voltage_Peak_V,"o-",color=ACCENT,ms=4)
ax.axhline(cap_limit_v,color=ACCENT2,ls="--",lw=1.6,label=f"{cap_limit_v:g} V procurement limit")
ax.fill_between(sub2.Flux_Loss_Pct,0,cap_limit_v,color=ACCENT3,alpha=0.12)
ax.set_yscale("log"); ax.set_xlabel("Flux loss (%)"); ax.set_ylabel("Cap peak voltage (V, log)")
ax.set_title(f"Capacitor Voltage Feasibility vs Flux Loss ({f0/1e3:.0f} kHz, Np=160)"); ax.legend()
fig.tight_layout(); fig.savefig(f"{FIGDIR}/07_capacitor_feasibility.png"); plt.close(fig)

# Fig 08 -- wire gauge trade-off at the sampled flux-loss value nearest 99%.
# Higher AWG means thinner wire, hence more resistance and more drive voltage.
flt=min(csv.Flux_Loss_Pct.unique(),key=lambda v:abs(v-99.0))
subg=csv[(csv.Frequency_Hz==config.FREQUENCY_HZ)&(csv.Primary_Turns_Np==160)&(csv.Flux_Loss_Pct==flt)].sort_values("Wire_Gauge_AWG")
fig,ax=plt.subplots(figsize=(7.8,5.4))
ax.plot(subg.Wire_Gauge_AWG,subg.Resonant_Voltage_Peak_V,"o-",color=ACCENT,label="Resonant V")
ax.set_xlabel("Wire gauge (AWG - higher=thinner)"); ax.set_ylabel("Resonant drive V (peak)",color=ACCENT)
ax.tick_params(axis="y",labelcolor=ACCENT)
ax2=ax.twinx(); ax2.grid(False)
ax2.plot(subg.Wire_Gauge_AWG,subg.Peak_Current_A,"s--",color=ACCENT2,label="Peak current")
ax2.set_ylabel("Peak current (A)",color=ACCENT2); ax2.tick_params(axis="y",labelcolor=ACCENT2)
ax.set_title(f"Effect of Wire Gauge ({f0/1e3:.0f} kHz, Np=160, flux loss {flt:g}%)")
fig.tight_layout(); fig.savefig(f"{FIGDIR}/08_wire_gauge.png"); plt.close(fig)

# Fig 09 -- one scaled design point (config.DESIGN_TURNS turns,
# config.DESIGN_AREA_M2 per coil), computed from the config FEMM anchor.
# Mirrors summary.py: the required primary current, the resonant drive
# voltage, and the resonant capacitor value at the low end of the swept band
# and at the operating point. Area scaling is extrapolated, not FEMM-verified.
Np_d=Ns_d=config.DESIGN_TURNS; Ap_d=As_d=config.DESIGN_AREA_M2
wr=config.WIRE_RADIUS_M
rp_d=np.sqrt(Ap_d/np.pi)
M_d=config.M0_H*(Np_d/N0)*(Ns_d/N0)*(Ap_d/config.A_REF_M2)*(As_d/config.A_REF_M2)
# Self-inductance of the primary, thin-wire single-loop formula.
Lp_d=mu0*Np_d**2*rp_d*(np.log(8*rp_d/wr)-2.0)
Rdc_d=rho*(Np_d*2*np.pi*rp_d)/(np.pi*wr**2)
# Both frequencies in kHz, from config (sweep start and operating point).
freqs=[config.FREQ_SWEEP_START_HZ/1e3,f0/1e3]; ip=[]; vpr=[]; cap=[]
for fk in freqs:
    om=2*np.pi*fk*1e3
    # Faraday inverted: current needed for the configured target Vpp signal.
    ipk=(config.DESIGN_TARGET_VPP/2)/(om*M_d)
    # At resonance only R_ac is left to drive (x2 for peak-to-peak), and the
    # series capacitor that cancels omega*L is C = 1/(omega^2 * L), in nF.
    ip.append(ipk); vpr.append(2*ipk*acr(Rdc_d,wr,fk*1e3)); cap.append(1e9/(om**2*Lp_d))
x=np.arange(len(freqs))
fig,axs=plt.subplots(1,3,figsize=(11.5,4.0))
for ax,data,ttl,col,unit in zip(axs,[ip,vpr,cap],
    ["Required peak current","Resonant drive voltage","Resonant capacitor"],
    [ACCENT,ACCENT3,ACCENT2],["A","Vpp","nF"]):
    ax.bar(x,data,0.6,color=col)
    for xi,d in zip(x,data): ax.text(xi,d,f"{d:.3g} {unit}",ha="center",va="bottom",fontsize=9)
    ax.set_xticks(x); ax.set_xticklabels([f"{fq:g} kHz" for fq in freqs]); ax.set_title(ttl,fontsize=10); ax.margins(y=0.18)
fig.suptitle(f"Resonant-Matched Operating Point (analytic M={M_d*1e6:.1f} uH, "
             f"{config.DESIGN_TARGET_VPP:g} Vpp target; area scaling extrapolated)")
fig.tight_layout(); fig.savefig(f"{FIGDIR}/09_operating_point.png"); plt.close(fig)
print("Figures:",sorted(os.listdir(FIGDIR)))
