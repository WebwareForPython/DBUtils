#!/usr/bin/env python

"""
clean.py - Clean up Webware installation directory.

Removes all derived and temporary files.
This will work on all operating systems.

"""

# The files that shall be removed:

files = '''
*~
*.bak
*.pyc
*.pyo
CGIWrapper/Errors.csv
CGIWrapper/Scripts.csv
CGIWrapper/ErrorMsgs/*.html
WebKit/*.pid
WebKit/*.address
WebKit/Logs/*.csv
WebKit/ErrorMsgs/*.html
'''

import os
from glob import glob

def remove(pattern):
	for name in glob(pattern):
		os.remove(name)

def walk_remove(pattern, dirname, names):
	pattern = os.path.join(dirname, pattern)
	remove(pattern)

if __name__ == '__main__':
	print "Cleaning up..."
	for pattern in files.splitlines():
		if pattern:
			print pattern
			if '/' in pattern:
				remove(pattern)
			else:
				os.path.walk('.', walk_remove, pattern)
