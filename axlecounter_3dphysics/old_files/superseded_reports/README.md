# Superseded reports

Moved here 2026-08-05. **Do not cite these — every number in them is stale.**

| File | Why it was retired |
|---|---|
| `Axle_Counter_3DPhysics_Full_Report.pdf` | 14 pages, revised 2026-07-31. Byline read "Prepared for Kanna". |
| `Axle_Counter_Run_Report.pdf` | 5 pages, same vintage. |

Two problems, both now fixed:

1. **Neither had a generator.** No script in the repo produced them, so they
   could not be rebuilt and drifted out of date every time the model changed.
2. **They describe the pre-rebuild model** — 100 turns, 11.06 mm coil radius,
   120.84 mm separation, M0 = 0.9269 uH, 91.7 % detection dip. The project now
   runs one canonical coil: 212 turns, 35 mm radius, 164.06 mm separation,
   M0 = 21.465 uH, 87.99 % dip.

## The current report

`reports/Axle_Counter_Full_Report.md` and `.pdf`, built by
`analysis_and_reporting/build_report.py` (stage 14 of `run_all.py`). Every value
in it is read from `config.py` and `reports/` at build time, so it cannot go
stale. Prepared by Rudranarayan.

```bash
cd axlecounter_3dphysics
py -3 analysis_and_reporting/build_report.py
```
