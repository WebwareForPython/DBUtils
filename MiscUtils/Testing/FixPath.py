"""
Fixes the Python path to start with our parent directory.

Merely importing this module fixes the path.

Doing this _guarantees_ that we're testing our local classes and not
some other installation. For those of us who have multiple instances
of Webware present, this is critical. For those who do not, this
doesn't hurt anything.
"""

import os, sys
sys.path.insert(0, os.path.abspath(os.pardir))

progPath = os.path.normpath(os.path.join(os.getcwd(), sys.argv[0]))
progDir = os.path.dirname(progPath)
