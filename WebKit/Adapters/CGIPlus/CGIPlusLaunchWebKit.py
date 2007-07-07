#!/usr/bin/env python

import os, sys

webwarePath = '/usr/local/Webware'
appWorkPath = '/usr/local/Webware'


def main(args):
	global webwarePath, appWorkPath
	newArgs = []
	for arg in args:
		if arg.startswith('--webware-dir='):
			webwarePath = arg[14:]
		elif arg.startswith('--work-dir='):
			appWorkPath = arg[11:]
		else:
			newArgs.append(arg)
	args = newArgs
	# ensure Webware is on sys.path
	sys.path.insert(0, webwarePath)

	# import the master launcher
	import WebKit.Launch

	if len(args) < 2:
		WebKit.Launch.usage()

	# Go!
	WebKit.Launch.launchWebKit(args[1], appWorkPath, args[2:])


if __name__=='__main__':
	main(sys.argv)
