#!/$1$DKA200/TOOLS/python/vms/bin/python.exe.1

import os, sys

webwarePath = '/webware092_root'
appWorkPath = '/webware092_root'


def main(args):
	global webwarePath, appWorkPath
	newArgs = []
	for arg in args:
		if arg.startswith('--webware-path='):
			webwarePath = arg[15:]
		elif arg.startswith('--working-path='):
			appWorkPath = arg[15:]
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
