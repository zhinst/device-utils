"""The Zurich Instruments Device Utils (zhinst-deviceutils)

This package is a collection of device utils for mid level device
control. Based on the native interface to zhinst-ziPython,
they offer an easy and user-friendly way to control Zurich Instruments
devices.
"""

try:
    from zhinst.deviceutils._version import version as __version__
except ModuleNotFoundError:
    pass
