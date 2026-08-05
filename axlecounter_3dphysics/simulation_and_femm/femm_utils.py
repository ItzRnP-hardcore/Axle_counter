"""
Shared FEMM helpers used by the solver scripts in this folder.

Provides one place to:
  * open the base model (or a scratch copy of it),
  * set the solver operating point (magnetostatic vs time-harmonic),
  * read mutual inductance out of a finished solution.

Requires the `femm` package + a FEMM install (Windows). The import is deferred
into _femm() so this module can still be imported on machines without FEMM.
"""
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config


def _femm():
    """Import and return the `femm` module lazily (FEMM is Windows-only)."""
    import femm
    return femm


def set_frequency(freq_hz=None):
    """Switch the open FEMM document to the given excitation frequency.

    The frequency is what selects the solver mode:
      freq_hz = 0    -> magnetostatic
      freq_hz > 0    -> time-harmonic (eddy currents in the steel rail, skin
                        effect in the copper -- the physically correct mode
                        for a 10-20 kHz axle counter).

    Defaults to config.FREQUENCY_HZ when freq_hz is not given. Returns the
    frequency that was actually applied.
    """
    femm = _femm()
    if freq_hz is None:
        freq_hz = config.FREQUENCY_HZ
    # mi_probdef(frequency, units, type, precision, depth, minangle, acsolver)
    # Depth = the real coil's axial length. A 2D planar solve reports flux per
    # unit depth, so this argument must be config.COIL_DEPTH_MM for absolute
    # flux / M / voltage to be physical rather than per-mm.
    femm.mi_probdef(freq_hz, "millimeters", "planar", 1e-8,
                    config.COIL_DEPTH_MM, 30, 0)
    return freq_hz


def extract_mutual_inductance():
    """Return (M_uH, rx_voltage, rx_flux, tx_current) from the loaded solution.

    Requires mi_analyze() + mi_loadsolution() to have run already. TX is the
    energised circuit ("New Circuit", FEMM group 2, the RIGHT/+x coil); RX is
    the open sense circuit ("Receiver", group 1, the LEFT/-x coil).
    """
    femm = _femm()
    # mo_getcircuitproperties returns [current, voltage, flux_linkage] for the
    # named circuit. Values are complex in a time-harmonic solve, hence abs().
    rx = femm.mo_getcircuitproperties(config.RX_CIRCUIT)   # [I, V, flux]
    tx = femm.mo_getcircuitproperties(config.TX_CIRCUIT)
    rx_voltage = abs(rx[1])
    rx_flux = abs(rx[2])
    tx_current = abs(tx[0])
    # Mutual inductance: flux linked by RX per amp of TX drive, in microhenries.
    M_uH = (rx_flux / tx_current) * 1e6 if tx_current > 0 else 0.0
    return M_uH, rx_voltage, rx_flux, tx_current


def open_base(set_ac=True):
    """Open the base FEM file and (optionally) switch to the AC operating point.

    Read-only inspection only: do NOT call mi_analyze() on a document opened
    this way, because FEMM auto-saves the open document when it analyzes and
    would overwrite the base model. Use open_scratch() for anything that
    solves.
    """
    femm = _femm()
    femm.opendocument(config.FEM_FILE)
    if set_ac:
        set_frequency(config.FREQUENCY_HZ)


def open_scratch(work_name, set_ac=True):
    """Open the base FEM file and immediately save-as a scratch copy.

    FEMM auto-saves the open document when it analyzes, so any script that
    calls mi_analyze() on the base file silently mutates it. Saving-as first
    redirects every later write to a throwaway file, leaving the base model
    untouched. `work_name` is a filename (placed in config.BASE_DIR) or an
    absolute path. Returns the scratch path.
    """
    import os
    femm = _femm()
    path = work_name if os.path.isabs(work_name) else os.path.join(config.BASE_DIR, work_name)
    femm.opendocument(config.FEM_FILE)
    # From here on the in-memory document is bound to `path`, not FEM_FILE.
    femm.mi_saveas(path)
    if set_ac:
        set_frequency(config.FREQUENCY_HZ)
    return path
