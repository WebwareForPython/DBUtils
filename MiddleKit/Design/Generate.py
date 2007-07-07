#!/usr/bin/env python
"""
Generate.py

> python Generate.py -h
"""


import os, string, sys, types
from getopt import getopt
import FixPath
import MiddleKit
from MiscUtils import StringTypes

if sys.platform == 'win32':
	# without this, I can't see output from uncaught exceptions!
	# perhaps this is caused by the recent incorporation of win32all (via DataTable)?
	sys.stderr = sys.stdout


class Generate:

	def databases(self):
		return ['MSSQL', 'MySQL', 'PostgreSQL']  # @@ 2000-10-19 ce: should build this dynamically

	def main(self, args=sys.argv):
		opt = self.options(args)

		# Make or check the output directory
		outdir = opt['outdir']
		if not os.path.exists(outdir):
			os.mkdir(outdir)
		elif not os.path.isdir(outdir):
			print 'Error: Output target, %s, is not a directory.' % outdir

		# Generate
		if opt.has_key('sql'):
			print 'Generating SQL...'
			self.generate(
				pyClass = opt['db'] + 'SQLGenerator',
				model = opt['model'],
				configFilename = opt.get('config'),
				outdir = os.path.join(outdir, 'GeneratedSQL'))
		if opt.has_key('py'):
			print 'Generating Python...'
			self.generate(
				pyClass = opt['db'] + 'PythonGenerator',
				model = opt['model'],
				configFilename = opt.get('config'),
				outdir=outdir)
		model = MiddleKit.Core.Model.Model(opt['model'],
			configFilename=opt.get('config'), havePythonClasses=0)
		model.printWarnings()

	def usage(self, errorMsg=None):
		progName = os.path.basename(sys.argv[0])
		if errorMsg:
			print '%s: error: %s' % (progName, errorMsg)
		print 'Usage: %s --db DBNAME --model FILENAME [--sql] [--py] [--config FILENAME] [--outdir DIRNAME]' % progName
		print '       %s -h | --help' % progName
		print
		print '       * Known databases include: %s' % ', '.join(self.databases())
		print '       * If neither --sql nor --py are specified, both are generated.'
		print '       * If --outdir is not specified, then the base filename (sans extension) is used.'
		print '       * --config lets you specify a different config filename inside the model.'
		print '         This is mostly useful for the regression test suite.'
		print
		sys.exit(1)

	def options(self, args):
		# Command line dissection
		if type(args) == type(''):
			args = args.split()
		optPairs, files = getopt(args[1:], 'h', ['help', 'db=', 'model=', 'sql', 'py', 'config=', 'outdir='])
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
		if not opt.has_key('sql') and not opt.has_key('py'):
			opt['sql'] = ''
			opt['py'] = ''
		if not opt.has_key('outdir'):
			opt['outdir'] = os.curdir

		return opt

	def generate(self, pyClass, model, configFilename, outdir):
		""" Generates code using the given class, model and output directory. The pyClass may be a string, in which case a module of the same name is imported and the class extracted from that. The model may be a string, in which case it is considered a filename of a model. """
		if type(pyClass) in StringTypes:
			module = __import__(pyClass, globals())
			pyClass = getattr(module, pyClass)
		generator = pyClass()
		if type(model) in StringTypes:
			generator.readModelFileNamed(model, configFilename=configFilename,
				havePythonClasses=0)
		else:
			generator.setModel(model)
		generator.generate(outdir)


if __name__ == '__main__':
	Generate().main(sys.argv)
