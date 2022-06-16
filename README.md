[![PyPI version](https://badge.fury.io/py/zhinst-deviceutils.svg)](https://badge.fury.io/py/zhinst-deviceutils)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/ambv/black)
[![Twitter URL](https://img.shields.io/twitter/url/https/twitter.com/fold_left.svg?style=social&label=Follow%20%40zhinst)](https://twitter.com/zhinst)

# Device Utils for Zurich Instruments

zhinst-deviceutils provides a set of helper functions for the native LabOne Python API
called [zhinst.ziPython](https://pypi.org/project/zhinst/).

It offers higher level functions to ease the communication with
[Zurich Instruments](https://zhinst.com) devices. It is not intended to be a
seperate layer above ``zhinst.ziPython`` but rather as an addition.

It currently has utility functions for the following devices:
* SHFQA
* SHFSG
* SHFQC

To see the device utils in action check out the
[LabOne API examples](https://github.com/zhinst/labone-api-examples).

## Installation
Python 3.7+ is required.
```
pip install zhinst-deviceutils
```

## Usage
```
import zhinst.deviceutils.shfqa
import zhinst.deviceutils.shfsg
import zhinst.deviceutils.shfqc

help(zhinst.deviceutils.shfqa)
help(zhinst.deviceutils.shfsg)
help(zhinst.deviceutils.shfqc)
```

## About

More information about programming with Zurich Instruments devices is available in the
[package documentation](https://docs.zhinst.com/zhinst-deviceutils/en/latest/)
and the
[LabOne Programming Manual](https://docs.zhinst.com/labone_programming_manual/overview.html).
