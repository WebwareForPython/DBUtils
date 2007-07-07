"""
FixPath.py

Enhance sys.path so that we're guaranteed to import the MiddleKit that
we reside in. This is particularly important for Webware developers
that might have more than one Webware source tree on their file system.
"""


# We're located at .../MiddleKit/Run/Tests/Test.py.
import os, sys

# this very next fix makes the MK test suite work for me (using Python 2.3.2, Webware CVS post 0.8, Windows XP Pro SP1)
if sys.path[0] not in ('', '.'):
	sys.path.insert(0, '')

# now make the fix referenced in the doc string
if sys.path and sys.path[0] == '':
	index = 1
else:
	index = 0
sys.path.insert(index, os.path.abspath('../..'))
import MiddleKit
