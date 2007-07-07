debug = 0

def contextInitialize(app, ctxPath):
	import os, sys

	try:
		import MiddleKit
	except ImportError:
		sys.path.insert(1, os.path.normpath(os.path.join(ctxPath, os.pardir, os.pardir)))
		import MiddleKit

	if debug:
		sys.stdout.flush()
		print '>> MiddleKit:', MiddleKit
		print '>> getcwd:', os.getcwd()
		print '>> sys.path:'
		print '\n'.join(sys.path)

	# Apply the automatic mixins.
	import MixIns
