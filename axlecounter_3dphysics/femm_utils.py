"""
Shared FEMM helpers.

Removes the copy-pasted open/analyze/extract logic from axle.py, femm_sweep.py
and apply_best_geom.py, and adds a single place to switch the solver between
magnetostatic and time-harmonic (AC) operation.

Requires the `femm` package + a FEMM install (Windows). Import is deferred so
that this module can be imported on machines without FEMM for tooling/tests.
"""
import config


def _femm():
    import femm
    return femm


def set_frequency(freq_hz=None):
    """Switch the open FEMM document to the given excitation frequency.

    freq_hz = 0    -> magnetostatic
    freq_hz > 0    -> time-harmonic (eddy currents in the steel rail, skin
                      effect in the copper -- the physically correct mode for
                      a 10-20 kHz axle counter).
    """
    femm = _femm()
    if freq_hz is None:
        freq_hz = config.FREQUENCY_HZ
    # mi_probdef(frequency, units, type, precision, depth, minangle, acsolver)
    femm.mi_probdef(freq_hz, "millimeters", "planar", 1e-8, 1, 30, 0)
    return freq_hz


def extract_mutual_inductance():
    """Return (M_uH, rx_voltage, rx_flux, tx_current) from the loaded solution."""
    femm = _femm()
    rx = femm.mo_getcircuitproperties(config.RX_CIRCUIT)   # [I, V, flux]
    tx = femm.mo_getcircuitproperties(config.TX_CIRCUIT)
    rx_voltage = abs(rx[1])
    rx_flux = abs(rx[2])
    tx_current = abs(tx[0])
    M_uH = (rx_flux / tx_current) * 1e6 if tx_current > 0 else 0.0
    return M_uH, rx_voltage, rx_flux, tx_current


def open_base(set_ac=True):
    """Open the base FEM file and (optionally) switch to the AC operating point."""
    femm = _femm()
    femm.opendocument(config.FEM_FILE)
    if set_ac:
        set_frequency(config.FREQUENCY_HZ)
