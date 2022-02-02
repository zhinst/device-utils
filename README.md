# Device Utils for the Zurich Instrument Devices

zhinst-deviceutils provides a set of helper functions for the native LabOne API called [zhinst.ziPython](https://pypi.org/project/zhinst/).
It offers higher level functions to ease the communication with [Zurich Instruments](https://zhinst.com) devices. It is not intendet to be a seperat layer above ``zhinst.ziPython`` but rather as an addition.

It has utility functions for the following devices:
* SHFQA
* SHFSG

other my follow soon.

## Installation
Python 3.6+ is required.
```
pip install zhinst-deviceutils
```

## Usage
```
import zhinst.deviceutils.shfqa
import zhinst.deviceutils.shfsg

help(zhinst.deviceutils.shfqa)
help(zhinst.deviceutils.shfsg)
```

## About

More information about programming with Zurich Instruments devices is available in the
[package documentation](http://docs.pages.zhinst.com/manuals/zhinst-deviceutils/index.html)
and the
[LabOne Programming Manual](https://docs.zhinst.com/labone_programming_manual/overview.html).
