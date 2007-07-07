"""Common globals.

The Common module provides some commmon globals to all modules/classes in
WebKit. It's intended for internal use, not for modules outside the WebKit.

Typically usage is::

	from Common import *

The globals provided are:
* the modules: `os`, `sys`, `time`
* the class `StringIO`
* the root class `Object`
* the names `True` and `False` for older Python versions
* the package `WebUtils`
* the exception class `AbstractError` that methods of abstract classes can raise
* the singleton `NoDefault`  for initializing default arguments
* the method `asclocaltime` for building time stamps in log files

"""

import os, sys, time

try: # for Python < 2.3
	True, False
except NameError:
	True, False = 1, 0

from Object import Object
import WebUtils
from MiscUtils import StringIO, AbstractError, NoDefault

def asclocaltime(t = None):
	"""Return a readable string of the current, local time.

	Useful for time stamps in log files.

	"""
	if t is None:
		t = time.time()
	return time.asctime(time.localtime(t))
