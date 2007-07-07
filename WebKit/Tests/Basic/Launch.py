#!/usr/bin/env python

import os, sys

scriptName = sys.argv and sys.argv[0]
if not scriptName or scriptName == '-c':
	scriptName = 'Launch.py'
workDir = os.path.dirname(os.path.abspath(scriptName))
os.chdir(workDir)
webwareDir = os.path.join(os.pardir, os.pardir, os.pardir)
sys.path.insert(0, webwareDir)

from WebKit import Launch

Launch.webwareDir = webwareDir

if __name__ == '__main__':
	Launch.main()
