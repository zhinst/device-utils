# Device Utils for the Zurich Instrument Devices

zhinst-deviceutils is an intermediate layer above the [zhinst.ziPython](https://pypi.org/project/zhinst/) module.
It offers higher level functions to ease the communication with [Zurich Instruments](https://zhinst.com) devices.

It has utility functions for the following devices:
* SHFQA

## Installation
Python 3.5+ is required.
```
pip install zhinst-deviceutils
```
Or
```
python -m pip install zhinst-deviceutils
```

## Usage
```
from zhinst.deviceutils import SHFQA

help(SHFQA)

```

## About

More information about programming with Zurich Instruments devices is available in the [package documentation](http://docs.pages.zhinst.com/manuals/zhinst-deviceutils/index.html) and the [LabOne Programming Manual](https://docs.zhinst.com/labone_programming_manual/overview.html).
