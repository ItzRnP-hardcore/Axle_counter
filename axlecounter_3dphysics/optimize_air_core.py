"""
Air-core coil optimisation for an inductive AXLE COUNTER (wheel detector).

NO ferrite core. TX and RX coils couple through open air across the rail. A
passing steel wheel/flange perturbs the field (eddy-current shunting + detuning)
so the RX signal DIPS -- that dip is the axle count. Design goal: the strongest,
most stable AIR-ONLY baseline coupling, so the wheel dip has good SNR.

Key coupling identity (both coils identical, series/parallel resonant):
  RX open-circuit signal  V_rx = w * M * Ip
  Tuning-cap voltage      V_cap = Ip * w * L
  => V_rx / V_cap = M / L  (a fixed ratio for the geometry)
So the measured signal is LIMITED BY THE CAPACITOR VOLTAGE RATING. Higher signal
=> higher cap voltage. This drives the design table below.
"""
import os
import numpy as np, json
import config

mu0 = 4e-7*np.pi
rho = 1.68e-8
r_eff   = config.COIL_RADIUS_M   # effective coil radius (m) ~ FEM model coil size
Ip_peak = 5.0            # max primary drive current (A peak)
Lwire_max = 500.0        # max wire length per coil (m)
f_op    = 25e3           # operating frequency (Hz)
Q_REAL  = 100.0          # realistic loaded Q of a solid-wire air coil @25 kHz
                         # (proximity + dielectric losses; use litz for higher)
GAUGE   = ("AWG16", 0.646e-3)   # thick wire for 5 A + low resistance

w = 2*np.pi*f_op
a = GAUGE[1]
M_ref = config.M0_H      # H, verified FEMM anchor at Np=Ns=100 (measured at
                         # 20 kHz; M is treated as geometry-dominated here)

def mutual_H(N):  return M_ref*(N/100.0)**2
def self_L(N):    return mu0*N**2*r_eff*(np.log(8*r_eff/a)-2.0)
def ac_R(N,f):
    lwire=N*2*np.pi*r_eff
    Rdc=rho*lwire/(np.pi*a**2)
    delta=np.sqrt(rho/(np.pi*f*mu0)); x=a/delta
    fac=1+x**4/48 if x<1 else x/2+0.75+3/(32*x)
    return Rdc*fac, lwire, delta

# ---- Design table across available capacitor voltage ratings ---------------
cap_ratings = [250, 630, 1000, 2000]   # V peak (standard film-cap classes)
rows=[]
for Vcap_max in cap_ratings:
    # largest N whose cap voltage stays within rating (V_cap = Ip*w*L)
    N=20; bestN=None
    while N < int(Lwire_max/(2*np.pi*r_eff)):
        L=self_L(N); Vcap=Ip_peak*w*L
        if Vcap<=Vcap_max: bestN=N
        else: break
        N+=1
    if bestN is None:
        print(f"  (skipping {Vcap_max} V class: cap voltage exceeds rating "
              f"even at N=20)")
        continue
    N=bestN
    L=self_L(N); R,lwire,delta=ac_R(N,f_op)
    M=mutual_H(N)
    Vrx_oc=w*M*Ip_peak
    Vrx_tuned=Q_REAL*Vrx_oc
    Cp=1/(w**2*L)
    rows.append(dict(Vcap=Vcap_max,N=N,L_mH=L*1e3,M_uH=M*1e6,R=R,lwire=lwire,
        Vrx_oc_mV=Vrx_oc*1e3,Vrx_tuned_V=Vrx_tuned,Cp_nF=Cp*1e9,
        Vdrive=Ip_peak*R,flux_uWb=M*Ip_peak*1e6,Ploss=0.5*Ip_peak**2*R))

print("="*96)
print(f"AIR-CORE DESIGN TABLE  (f={f_op/1e3:.0f} kHz, Ip={Ip_peak} A, coil dia {2*r_eff*1e3:.0f} mm, {GAUGE[0]}, Q~{Q_REAL:.0f})")
print("="*96)
hdr=f"{'Cap V':>6} {'Turns':>6} {'L(mH)':>7} {'M(uH)':>7} {'R(ohm)':>7} {'Vrx_oc':>9} {'Vrx_tuned':>10} {'Cp(nF)':>7} {'Vdrive':>7}"
print(hdr); print("-"*96)
for r in rows:
    print(f"{r['Vcap']:>6} {r['N']:>6} {r['L_mH']:>7.2f} {r['M_uH']:>7.4f} {r['R']:>7.3f} "
          f"{r['Vrx_oc_mV']:>7.1f}mV {r['Vrx_tuned_V']:>9.2f}V {r['Cp_nF']:>7.2f} {r['Vdrive']:>6.2f}V")
print("="*96)

# ---- Recommended design: the 1000 V class (good signal, standard cap) -------
rec_list=[r for r in rows if r["Vcap"]==1000]
if not rec_list:
    raise SystemExit("No feasible 1000 V design row -- inspect the table above.")
rec=rec_list[0]
# skin depth depends only on f_op -- compute it directly rather than relying
# on the loop variable leaking out of the last iteration
delta=np.sqrt(rho/(np.pi*f_op*mu0))
rec.update(dict(f_kHz=f_op/1e3, gauge=GAUGE[0], wire_radius_mm=a*1e3,
    coil_dia_mm=2*r_eff*1e3, Ip_A=Ip_peak, Q=Q_REAL, skin_mm=delta*1e3,
    Cs_nF=rec["Cp_nF"]))
with open(os.path.join(config.OUTPUT_DIR, "optimal_design.json"), "w") as f:
    json.dump({"table":rows,"recommended":rec}, f, indent=2)
print("\nRECOMMENDED (1000 V cap class):")
for k in ["N","L_mH","M_uH","R","lwire","Vrx_oc_mV","Vrx_tuned_V","Cp_nF","Vdrive","Ploss"]:
    print(f"  {k:12}: {rec[k]:.4f}" if isinstance(rec[k],float) else f"  {k:12}: {rec[k]}")
print("Saved reports/optimal_design.json")
