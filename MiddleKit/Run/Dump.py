#!/usr/bin/env python
"""
Dump.py

> python Dump.py -h
"""


import os, string, sys, types
from getopt import getopt


def FixPathForMiddleKit(verbose=0):
	"""
	Enhances sys.path so that Dump.py can import MiddleKit.whatever.
	We *always* enhance the sys.path so that Dump.py is using the MiddleKit that contains him, as opposed to whatever happens to be found first in the Python path. That's an subtle but important feature for those of us who sometimes have more than one MiddleKit on our systems.
	"""
	v = verbose
	import os, sys
	if globals().has_key('__file__'):
		# We were imported as a module
		location = __file__
		if v:
			print 'took location from __file__'
	else:
		# We were executed directly
		location = sys.argv[0]
		if v:
			print 'took location from sys.argv[0]'

	if v:
		print 'location =', location
	if location.lower() == 'dump.py':
		# The simple case. We're at MiddleKit/Design/Dump.py
		location = os.path.abspath('../../')
	else:
		# location will basically be:
		# .../MiddleKit/Design/Dump.py
		if os.name == 'nt':
			# Case insenstive file systems:
			location = location.lower()
			what = 'middlekit'
		else:
			what = 'MiddleKit'
		if location.find(what) != -1:
			if v:
				print 'MiddleKit in location'
			index = location.index(what)
			location = location[:index]
			if v:
				print 'new location =', location
		location = os.path.abspath(location)
		if v:
			print 'final location =', location
	sys.path.insert(1, location)
	if v:
		print 'path =', sys.path
		print
		print 'importing MiddleKit...'
	import MiddleKit
	if v:
		print 'done.'

FixPathForMiddleKit()
import MiddleKit


class Dump:

	def databases(self):
		return ['MSSQL', 'MySQL', 'PostgreSQL']  # @@ 2000-10-19 ce: should build this dynamically

	def main(self, args=sys.argv):
		opt = self.options(args)

		if opt.has_key('outfile'):
			out = open(opt['outfile'], 'w')
		else:
			out = None

		# this is really only necessary if 'package' is set for the model,
		# but it shouldn't hurt
		middledir = os.path.dirname(os.path.dirname((os.path.abspath(opt['model']))))
		sys.path.insert(1, middledir)

		# Dump
		classname = '%sObjectStore' % opt['db']
		module = __import__('MiddleKit.Run.%s' % classname, globals(), locals(), [classname])
		pyClass = getattr(module, classname)
		if opt.has_key('prompt-for-args'):
			sys.stderr.write('Enter %s init args: ' % classname)
			conn = raw_input()
			store = eval('pyClass(%s)' % conn)
		else:
			store = pyClass()
		store.readModelFileNamed(opt['model'])
		store.dumpObjectStore(out, progress=opt.has_key('show-progress'))

	def usage(self, errorMsg=None):
		progName = os.path.basename(sys.argv[0])
		if errorMsg:
			print '%s: error: %s' % (progName, errorMsg)
		print 'Usage: %s --db DBNAME --model FILENAME' % progName
		print '       %s -h | --help' % progName
		print
		print 'Options:'
		print '    --prompt-for-args Prompt for args to use for initializing store (i.e. password)'
		print '    --show-progress   Print a dot on stderr as each class is processed'
		print '                      (useful when dumping large databases)'
		print
		print '       * DBNAME can be: %s' % ', '.join(self.databases())
		print
		sys.exit(1)

	def options(self, args):
		# Command line dissection
		if type(args) == type(''):
			args = args.split()
		optPairs, files = getopt(args[1:], 'h', ['help',
			'show-progress', 'db=', 'model=', 'outfile=', 'prompt-for-args'])
		if len(optPairs) < 1:
			self.usage('Missing options.')
		if len(files) > 0:
			self.usage('Extra files or options passed.')

		# Turn the cmd line optPairs into a dictionary
		opt = {}
		for key, value in optPairs:
			if len(key) >= 2 and key[:2] == '--':
				key = key[2:]
			elif key[0] == '-':
				key = key[1:]
			opt[key] = value

		# Check for required opt, set defaults, etc.
		if opt.has_key('h') or opt.has_key('help'):
			self.usage()
		if not opt.has_key('db'):
			self.usage('No database specified.')
		if not opt.has_key('model'):
			self.usage('No model specified.')
		return opt


if __name__ == '__main__':
	Dump().main(sys.argv)
