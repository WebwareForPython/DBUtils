"""
TestCommon.py

This is just a convenience module for the various test modules (TestFoo.py).
"""


import os, string, sys, time
import FixPath
import MiscUtils
import MiddleKit
from MiddleKit.Core.Klasses import Klasses

workDir = 'WorkDir'

def rmdir(dirname, shouldPrint=1):
	""" Really remove the directory, even if it has files (and directories) in it. """
	if shouldPrint:
		print 'Removing %s...' % dirname
	if os.path.exists(dirname):
		exceptions = (os.curdir, os.pardir)
		for name in os.listdir(dirname):
			if name not in exceptions:
				fullName = os.path.join(dirname, name)
				if os.path.isdir(fullName):
					rmdir(fullName, shouldPrint=0)
				else:
					os.remove(fullName)
		os.rmdir(dirname)


dbName = 'MySQL'
	# passed as an cmd line arg to Generate.py, and used to find an object store module

storeArgs = {}
	# passed to the object store class

sqlCommand = 'mysql'
	# the database command used for feeding SQL to the database via stdin

sqlVersionCommand = 'mysql --version'
	# the database command used to get the version number of the SQL database


# override any of the preceding as needed by creating a LocalConfig.py:
try:
	from LocalConfig import *
except ImportError:
	pass
