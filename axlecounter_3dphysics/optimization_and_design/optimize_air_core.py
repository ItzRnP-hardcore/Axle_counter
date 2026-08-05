"""
Air-core coil optimisation for an inductive AXLE COUNTER (wheel detector).

NO ferrite core. TX and RX coils couple through open air across the rail. A
passing steel wheel/flange perturbs the field (eddy-current shunting + detuning)
so the RX signal DIPS -- that dip is the axle count. Design goal: the strongest,
most stable AIR-ONLY baseline coupling, so the wheel dip has good SNR.

Key coupling identity (both coils identical, series/parallel resonant):
  RX open-circuit signal  V_rx = w * M * Ip
      -- the changing TX current Ip induces a voltage in the RX coil equal to
         the rate of change of the shared flux, w * M * Ip.
  Tuning-cap voltage      V_cap = Ip * w * L
      -- at resonance the same current Ip flows through the TX coil's own
         reactance w*L, and the tuning capacitor sees that whole voltage.
  => V_rx / V_cap = M / L  (a fixed ratio for the geometry)
Because M/L is set by geometry alone, adding turns raises the received signal
and the capacitor voltage in lockstep. So the usable signal is LIMITED BY THE
CAPACITOR VOLTAGE RATING: for each standard rating there is a largest turn
count that stays within it. That is what the design table below computes.

Writes reports/optimal_design.json (the full table plus the recommended row).
"""
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import os
import numpy as np, json
import config

mu0 = 4e-7*np.pi         # permeability of free space (H/m)
rho = 1.68e-8            # resistivity of copper (ohm.m) at room temperature
r_eff   = config.COIL_RADIUS_M   # effective coil radius (m) ~ FEM model coil size
Ip_peak = 5.0            # max primary drive current (A peak)
Lwire_max = 500.0        # max wire length per coil (m)
f_op    = 25e3           # operating frequency (Hz)
Q_REAL  = 100.0          # realistic loaded Q of a solid-wire air coil @25 kHz
                         # (proximity + dielectric losses; use litz for higher)
GAUGE   = ("AWG16", 0.646e-3)   # thick wire for 5 A + low resistance

w = 2*np.pi*f_op         # angular frequency (rad/s)
a = GAUGE[1]             # wire conductor radius (m)
M_ref = config.M0_H      # H, verified FEMM anchor at Np=Ns=100 (measured at
                         # 20 kHz; M is treated as geometry-dominated here)

def mutual_H(N):
    """Mutual inductance at N turns per coil, scaled from the FEMM anchor.

    M ~ N^2 because both coils change together: N times the ampere-turns
    driving the flux, N times the linkage picking it up. This N^2 law is
    FEMM-verified.
    """
    return M_ref*(N/config.BASELINE_TURNS)**2

def self_L(N):
    """Self-inductance of one N-turn circular air coil (single-loop formula)."""
    return mu0*N**2*r_eff*(np.log(8*r_eff/a)-2.0)

def ac_R(N,f):
    """Approximate AC resistance of one coil at frequency f.

    Returns (R_ac, total wire length, skin depth). At high frequency current
    crowds into a surface layer of thickness delta, so the usable conductor
    cross-section shrinks and R rises above its DC value. `fac` is a standard
    closed-form approximation of that ratio in terms of x = a/delta: a small
    correction while the wire is thinner than a skin depth (x < 1), and
    roughly proportional to x once it is much thicker. This models skin effect
    only -- proximity effect between adjacent turns is not included, which is
    why Q_REAL above is set from measurement rather than derived here.
    """
    lwire=N*2*np.pi*r_eff
    Rdc=rho*lwire/(np.pi*a**2)
    delta=np.sqrt(rho/(np.pi*f*mu0)); x=a/delta
    fac=1+x**4/48 if x<1 else x/2+0.75+3/(32*x)
    return Rdc*fac, lwire, delta

# ---- Design table across available capacitor voltage ratings ---------------
cap_ratings = [250, 630, 1000, 2000]   # V peak (standard film-cap classes)
rows=[]
for Vcap_max in cap_ratings:
    # Largest N whose cap voltage stays within rating (V_cap = Ip*w*L). L grows
    # as N^2, so V_cap rises monotonically with N: step N up until the rating
    # is exceeded and keep the last turn count that passed. The loop also stops
    # once the wire length would exceed Lwire_max.
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
    # Characterise the winning turn count for this capacitor class.
    N=bestN
    L=self_L(N); R,lwire,delta=ac_R(N,f_op)
    M=mutual_H(N)
    Vrx_oc=w*M*Ip_peak          # raw open-circuit RX signal
    Vrx_tuned=Q_REAL*Vrx_oc     # after resonant step-up by the RX tank's Q
    Cp=1/(w**2*L)               # capacitance that resonates with L at f_op
    # Vdrive is the amplifier voltage needed to push Ip through the coil
    # resistance at resonance; Ploss is the time-averaged copper loss.
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
# 1000 V film caps are readily available while still allowing a high turn
# count, so this row is the recommended operating point.
rec_list=[r for r in rows if r["Vcap"]==1000]
if not rec_list:
    raise SystemExit("No feasible 1000 V design row -- inspect the table above.")
rec=rec_list[0]
# Skin depth depends only on f_op, so compute it directly here rather than
# relying on the value the loop above happened to leave behind.
delta=np.sqrt(rho/(np.pi*f_op*mu0))
# Attach the build parameters to the recommended row so the JSON is a
# self-contained coil specification.
rec.update(dict(f_kHz=f_op/1e3, gauge=GAUGE[0], wire_radius_mm=a*1e3,
    coil_dia_mm=2*r_eff*1e3, Ip_A=Ip_peak, Q=Q_REAL, skin_mm=delta*1e3,
    Cs_nF=rec["Cp_nF"]))
with open(os.path.join(config.OUTPUT_DIR, "optimal_design.json"), "w") as f:
    json.dump({"table":rows,"recommended":rec}, f, indent=2)
print("\nRECOMMENDED (1000 V cap class):")
for k in ["N","L_mH","M_uH","R","lwire","Vrx_oc_mV","Vrx_tuned_V","Cp_nF","Vdrive","Ploss"]:
    print(f"  {k:12}: {rec[k]:.4f}" if isinstance(rec[k],float) else f"  {k:12}: {rec[k]}")
print("Saved reports/optimal_design.json")
