#!/usr/bin/env python

"""install.py

Webware for Python installer

FUTURE
	* Look for an install.py in each component directory and run it
	  (there's not a strong need right now).
	* Use distutils or setuptools instead of our own plugin concept.

"""


import os, sys
from glob import glob

from MiscUtils import StringIO
from MiscUtils.PropertiesObject import PropertiesObject


class OutputCatcher:
	"""Auxiliary class for logging output."""

	def __init__(self, output, log):
		self._output = output
		self._log = log

	def write(self, stuff):
		if stuff:
			self._output.write(stuff)
			self._output.flush()
			self._log.append(stuff)


class Installer:
	"""Install Webware.

	The _comps attribute is a list of components,
	each of which is an instance of MiscUtils.PropertiesObject.

	"""


	## Init ##

	def __init__(self):
		self._props = PropertiesObject('Properties.py')
		self._props['dirname'] = '.'
		self._comps = []
		self._htHeader, self._htFooter = self.htHeaderAndFooter()
		from DocSupport.pytp import PyTP
		self._pytp = PyTP()
		from DocSupport.autotoc import AutoToC
		self._autotoc = AutoToC()


	## Debug printing facility ##

	def _nop (self, msg):
		pass

	def _printMsg (self, msg):
		print '  ' + msg


	## Running the installation ##

	def run(self, verbose=0, passprompt=1, defaultpass='', keepdocs=0):
		self._verbose = verbose
		self.printMsg = verbose and self._printMsg or self._nop
		log = []
		stdout, stderr = sys.stdout, sys.stderr
		try:
			sys.stdout = OutputCatcher(sys.stdout, log)
			sys.stderr = OutputCatcher(sys.stderr, log)
			self.printHello()
			self.clearLogFile()
			if not self.checkPyVersion() or not self.checkThreading():
				return
			self.detectComponents()
			self.installDocs(keepdocs)
			self.backupConfigs()
			self.copyStartScript()
			self.compileModules()
			self.fixPermissions()
			self.setupWebKitPassword(passprompt, defaultpass)
			self.printGoodbye()
			self.writeLogFile(log)
		finally:
			sys.stdout, sys.stderr = stdout, stderr

	def clearLogFile(self):
		"""Remove the install.log file.

		This file with the logged output will get created at the
		very end of the installation, provided there are no errors.
		"""
		if os.path.exists('install.log'):
			print 'Removing log from last installation...'
			os.remove('install.log')
			print

	def printHello(self):
		from time import time, localtime, asctime
		print '%(name)s %(versionString)s' % self._props
		print 'Installer'
		print
		self.printKeyValue('Cur Date', asctime(localtime(time())))
		self.printKeyValue('Python', sys.version.replace(') [', ')\n['))
		self.printKeyValue('Op Sys', os.name)
		self.printKeyValue('Platform', sys.platform)
		self.printKeyValue('Cur Dir', os.getcwd())
		print

	def checkPyVersion(self, minver=(2, 0)):
		"""Check for minimum required Python version."""
		try:
			ver = sys.version_info[:len(minver)]
		except AttributeError:
			ver = (1,)
		if ver < minver:
			print ('This Release of Webware requires Python %s.\n'
				'Your currently used version is Python %s.\n'
				'You can download a newer version at: http://www.python.org\n'
				% ('.'.join(map(str, minver)), '.'.join(map(str, ver))))
			response = raw_input('You may continue to install, '
				'but Webware may not perform as expected.\n'
				'Do you wish to continue with the installation?  [yes/no] ')
			return response[:1].upper() == "Y"
		return 1

	def checkThreading(self):
		try:
			import threading
		except ImportError:
			print ('Webware requires that Python be compiled with threading support.\n'
				'This version of Python does not appear to support threading.\n')
			response = raw_input('You may continue, '
				'but you will have to run the AppServer with a Python\n'
				'interpreter that has threading enabled.\n'
				'Do you wish to continue with the installation? [yes/no] ')
			return response[:1].upper() == "Y"
		return 1

	def detectComponents(self):
		print 'Scanning for components...'
		dirNames = filter(lambda dir: not dir.startswith('.')
				and os.path.isdir(dir), os.listdir(os.curdir))
		dirNames.sort()
		self._maxCompLen = max(map(len, dirNames))
		oldPyVersion = 0
		column = 0
		for dirName in dirNames:
			propName = dirName + '/Properties.py'
			try:
				print dirName.ljust(self._maxCompLen, '.'),
			except TypeError:
				print dirName.ljust(self._maxCompLen),
			if os.path.exists(propName):
				comp = PropertiesObject(propName)
				comp['dirname'] = dirName
				for key in self._props.keys():
					if not comp.has_key(key):
						comp[key] = self._props[key]
				if sys.version_info[:3] < comp['requiredPyVersion']:
					oldPyVersion += 1
					print 'no*',
				else:
					self._comps.append(comp)
					print 'yes',
			else:
				print 'no ',
			if column < 2 and not self._verbose:
				print '   ',
				column += 1
			else:
				print
				column = 0
		if column:
			print
		if oldPyVersion:
			print "* some components require a newer Python version"
		self._comps.sort(lambda a, b: cmp(a['name'], b['name']))
		print

	def setupWebKitPassword(self, prompt, defpass):
		"""Setup a password for WebKit Application server."""
		print 'Setting the WebKit password...'
		print
		if prompt:
			print 'Choose a password for the WebKit Application Server.'
			print 'If you will just press enter without entering anything,'
			if defpass is None:
				print 'a password will be automatically generated.'
			else:
				print 'the password specified on the command-line will be used.'
			from getpass import getpass
			password = getpass()
		else:
			if defpass is None:
				print 'A password will be automatically generated.'
			else:
				print 'A password was specified on the command-line.'
			password = None
		print 'You can check the password after installation at:'
		appConfig = 'WebKit/Configs/Application.config'
		print os.path.normpath(appConfig)
		if not password:
			if defpass is None:
				from string import letters, digits
				from random import choice
				password = ''.join(map(choice, [letters + digits]*8))
			else:
				password = defpass
		try: # read config file
			data = open(appConfig).read()
		except IOError:
			print 'Error reading Application.config file.'
			print 'Password not replaced, make sure to edit it by hand.'
			print
			return
		# This will search for the construct "'AdminPassword': '...'"
		# and replace '...' with the content of the 'password' variable:
		if data.lstrip().startswith('{'):
			pattern = "('AdminPassword'\s*:)\s*'.*?'"
		else: # keyword arguments style
			pattern = "(AdminPassword\\s*=)\\s*['\"].*?['\"]"
		repl = "\g<1> '%s'" % password.replace( # escape critical characters
			'\\', '\\\\\\\\').replace("'", "\\\\'").replace('%', '\\\\045')
		from re import subn
		data, count = subn(pattern, repl, data)
		if count != 1:
			print "Warning:",
			if count > 1:
				print "More than one 'AdminPassword' in config file."
			else:
				print "'AdminPassword' not found in config file."
			return
		try: # write back config file
			open(appConfig, 'w').write(data)
		except IOError:
			print 'Error writing Application.config (probably no permission).'
			print 'Password not replaced, make sure to edit it by hand.'
			print
			return
		print 'Password replaced successfully.'
		print

	def installDocs(self, keep):
		self.processHtmlDocFiles()
		self.processPyTemplateFiles(keep)
		self.createBrowsableSource()
		self.createComponentIndex()
		self.createComponentIndexes(keep)
		self.createDocContexts()

	def processHtmlDocFiles(self):
		print 'Processing html doc files...'
		for htmlFile in glob('Docs/*.html'):
			self.processHtmlDocFile(htmlFile)
		for comp in self._comps:
			dir = comp['dirname']
			for htmlFile in glob(dir + '/Docs/*.html'):
				self.processHtmlDocFile(htmlFile)
		print

	def processPyTemplateFiles(self, keep):
		print 'Processing phtml doc files...'
		if keep:
			print 'The templates will not be removed.'
		else:
			print 'The templates will be removed afterwards.'
		for inFile in glob('Docs/*.phtml'):
			if not os.path.splitext(inFile)[0].endswith('OfComponent'):
				self.processPyTemplateFile(inFile, self._props, keep)
		for comp in self._comps:
			dir = comp['dirname']
			for inFile in glob(dir + '/Docs/*.phtml'):
				self.processPyTemplateFile(inFile, comp, keep)
		print

	def createBrowsableSource(self):
		"""Create HTML docs for class hierarchies, summaries, sources etc."""
		print 'Creating html source, summaries and doc files...'
		column = 0
		for comp in self._comps:
			dir = comp['dirname']
			if self._verbose:
				print dir, '...'
			else:
				try:
					print dir.ljust(self._maxCompLen, '.'),
				except TypeError:
					print dir.ljust(self._maxCompLen),
			sourceDir = dir + '/Docs/Source'
			self.makeDir(sourceDir)
			filesDir = sourceDir + '/Files'
			self.makeDir(filesDir)
			summariesDir = sourceDir + '/Summaries'
			self.makeDir(summariesDir)
			docsDir = sourceDir + '/Docs'
			self.makeDir(docsDir)
			for pyFilename in glob(dir + '/*.py'):
				self.createHighlightedSource(pyFilename, filesDir)
				self.createPySummary(pyFilename, summariesDir)
				self.createPyDocs(pyFilename, docsDir)
			self.createPyDocs(dir, docsDir)
			self.createFileList(dir, sourceDir)
			self.createClassList(dir, sourceDir)
			if not self._verbose:
				print "ok",
				if column < 2:
					print '    ',
					column += 1
				else:
					print
					column = 0
		if column:
			print
		print

	def createHighlightedSource(self, filename, dir):
		"""Create highlighted HTML source code using py2html."""
		from DocSupport import py2html
		module = os.path.splitext(os.path.basename(filename))[0]
		targetName = '%s/%s.html' % (dir, module)
		self.printMsg('Creating %s...' % targetName)
		stdout = sys.stdout
		try:
			sys.stdout = StringIO()
			py2html.main((None, '-stdout', '-files', filename))
			result = sys.stdout.getvalue()
		finally:
			sys.stdout = stdout
		open(targetName, 'w').write(result)

	def createPySummary(self, filename, dir):
		"""Create a HTML module summary."""
		from DocSupport.PySummary import PySummary
		module = os.path.splitext(os.path.basename(filename))[0]
		targetName = '%s/%s.html' % (dir, module)
		self.printMsg('Creating %s...' % targetName)
		sum = PySummary()
		sum.readConfig('DocSupport/PySummary.config')
		sum.readFileNamed(filename)
		html = sum.html()
		open(targetName, 'w').write(html)

	def createPyDocs(self, filename, dir):
		"""Create a HTML module documentation using pydoc."""
		try:
			import pydoc
		except ImportError:
			from MiscUtils import pydoc
		package, module = os.path.split(filename)
		module = os.path.splitext(module)[0]
		if package:
			module = package + '.' + module
		targetName = '%s/%s.html' % (dir, module)
		self.printMsg('Creating %s...' % targetName)
		saveDir = os.getcwd()
		try:
			os.chdir(dir)
			targetName = '../' + targetName
			stdout = sys.stdout
			sys.stdout = StringIO()
			try:
				pydoc.writedoc(module)
			except Exception:
				pass
			msg = sys.stdout.getvalue()
			sys.stdout = stdout
			if msg:
				self.printMsg(msg)
		finally:
			os.chdir(saveDir)

	def createFileList(self, filesDir, docsDir):
		"""Create a HTML list of the source files."""
		from DocSupport.FileList import FileList
		name = os.path.basename(filesDir)
		self.printMsg('Creating file list of %s...' % name)
		filelist = FileList(name)
		saveDir = os.getcwd()
		os.chdir(filesDir)
		try:
			filelist.readFiles('*.py')
			targetName = '../' + docsDir + '/FileList.html'
			self.printMsg('Creating %s...' % targetName)
			filelist.printForWeb(targetName)
		finally:
			os.chdir(saveDir)

	def createClassList(self, filesDir, docsDir):
		"""Create a HTML class hierarchy listing of the source files."""
		from DocSupport.ClassList import ClassList
		name = os.path.basename(filesDir)
		self.printMsg('Creating class list of %s...' % name)
		classlist = ClassList(name)
		saveDir = os.getcwd()
		os.chdir(filesDir)
		try:
			classlist.readFiles('*.py')
			targetName = '../' + docsDir + '/ClassList.html'
			self.printMsg('Creating %s...' % targetName)
			classlist.printForWeb(0, targetName)
			targetName = '../' + docsDir + '/ClassHierarchy.html'
			self.printMsg('Creating %s...' % targetName)
			classlist.printForWeb(1, targetName)
		finally:
			os.chdir(saveDir)

	def createComponentIndex(self):
		"""Create a HTML component index of Webware itself."""
		print 'Creating ComponentIndex.html...'
		ht = ["<% header('Webware Documentation', 'titlebar',"
			" 'ComponentIndex.css') %>"]
		wr = ht.append
		wr('<p>Don\'t know where to start? '
			'Try <a href="../WebKit/Docs/index.html">WebKit</a>.</p>')
		wr('<table align="center" border="0" '
			'cellpadding="2" cellspacing="2" width="100%">')
		wr('<tr class="ComponentHeadings">'
			'<th>Component</th><th>Status</th><th>Ver</th>'
			'<th>Py</th><th>Summary</th></tr>')
		row = 0
		for comp in self._comps:
			comp['nameAsLink'] = ('<a href='
				'"../%(dirname)s/Docs/index.html">%(name)s</a>' % comp)
			comp['indexRow'] = row + 1
			wr('<tr valign="top" class="ComponentRow%(indexRow)i">'
				'<td class="NameVersionCell">'
				'<span class="Name">%(nameAsLink)s</span></td>'
				'<td>%(status)s</td>'
				'<td><span class="Version">%(versionString)s</span></td>'
				'<td>%(requiredPyVersionString)s</td>'
				'<td>%(synopsis)s</td></tr>' % comp)
			row = 1 - row
		wr('</table>')
		wr("<% footer() %>")
		ht = '\n'.join(ht)
		ht = self.processPyTemplate(ht, self._props)
		open('Docs/ComponentIndex.html', 'w').write(ht)

	def createComponentIndexes(self, keep):
		"""Create start page for all components."""
		indexfile = 'Docs/indexOfComponent.phtml'
		if not os.path.exists(indexfile):
			return
		print "Creating index.html for all components..."
		index = open(indexfile).read()
		link = '<p><a href="%s">%s</a></p>'
		for comp in self._comps:
			comp['webwareVersion'] = self._props['version']
			comp['webwareVersionString'] = self._props['versionString']
			# Create 'htDocs' as a HTML fragment corresponding to comp['docs']
			ht = []
			for doc in comp['docs']:
				ht.append(link % (doc['file'], doc['name']))
			ht = ''.join(ht)
			comp['htDocs'] = ht
			# Set up release notes
			ht = []
			files = glob(comp['dirname'] + '/Docs/RelNotes-*.html')
			if files:
				releaseNotes = []
				for filename in files:
					item = {'dirname': os.path.basename(filename)}
					filename = item['dirname']
					ver = filename[
						filename.rfind('-') + 1 : filename.rfind('.')]
					item['name'] = ver
					if ver == 'X.Y':
						item['ver'] = ver.split('.')
					else:
						i = 0
						while i < len(ver) and ver[i] in '.0123456789':
							i += 1
						if i:
							item['ver'] = map(int, ver[:i].split('.'))
					releaseNotes.append(item)
				releaseNotes.sort(lambda a, b: cmp(b['ver'], a['ver']))
				for item in releaseNotes:
					ht.append(link % (item['dirname'], item['name']))
			else:
				ht.append('<p>None</p>')
			ht = '\n'.join(ht)
			comp['htReleaseNotes'] = ht
			# Write file
			filename = comp['dirname'] + '/Docs/index.html'
			ht = self.processPyTemplate(index, comp)
			open(filename, 'w').write(ht)
		if not keep:
			os.remove(indexfile)
		print

	def createDocContexts(self):
		"""Create a WebKit context for every Docs directory."""
		print 'Making all Docs directories browsable via WebKit...'
		# Place an __init__.py file in every Docs directory
		docsDirs = ['Docs']
		for comp in self._comps:
			if comp.get('docs', None):
				docsDir = comp['dirname'] + '/Docs'
				if os.path.isdir(docsDir):
					docsDirs.append(docsDir)
		for docsDir in docsDirs:
			initFile = docsDir + '/__init__.py'
			if not os.path.exists(initFile) or 1:
				open(initFile, 'w').write(
					'# this can be browsed as a Webware context\n')
		# Copy favicon to the default context
		open('WebKit/Examples/favicon.ico', 'wb').write(
			open('Docs/favicon.ico', 'rb').read())
		print

	def backupConfigs(self):
		"""Copy *.config to *.config.default, if they don't already exist.

		This allows the user to always go back to the default config file if
		needed (for troubleshooting for example).

		"""
		print 'Creating backups of original config files...'
		self._backupConfigs(os.curdir)
		print

	def _backupConfigs(self, dir):
		for filename in os.listdir(dir):
			fullPath = os.path.join(dir, filename)
			if os.path.isdir(fullPath):
				self._backupConfigs(fullPath)
			elif (not filename.startswith('.') and
				os.path.splitext(filename)[1] == '.config'):
				self.printMsg(fullPath)
				backupPath = fullPath + '.default'
				if not os.path.exists(backupPath):
					open(backupPath, 'wb').write(open(fullPath, 'rb').read())

	def copyStartScript(self):
		"""Copy the most appropriate start script to WebKit/webkit."""
		if os.name == 'posix':
			print 'Copying start script...',
			ex = os.path.exists
			if ex('/etc/rc.status') and \
				ex('/sbin/startproc') and \
				ex('/sbin/killproc'):
				s = 'SuSE'
			elif ex('/etc/init.d/functions') or \
				ex('/etc/rc.d/init.d/functions'):
				s = 'RedHat'
			elif ex('/sbin/start-stop-daemon'):
				s = 'Debian'
			elif ex('/etc/rc.subr'):
				s = 'NetBSD'
			else:
				s = 'Generic'
			print s
			# Copy start script:
			s = 'WebKit/StartScripts/' + s
			t = 'WebKit/webkit'
			open(t, 'wb').write(open(s, 'rb').read())
			print

	def compileModules(self, force=0):
		"""Compile modules in all installed componentes."""
		from compileall import compile_dir
		print 'Byte compiling all modules...'
		for comp in self._comps:
			dir = comp['dirname']
			try:
				compile_dir(dir, force=force, quiet=1)
			except TypeError: # workaround for Python < 2.3
				stdout = sys.stdout
				sys.stdout = StringIO()
				compile_dir(dir, force=force)
				sys.stdout = stdout
		print

	def fixPermissions(self):
		if os.name == 'posix':
			print 'Setting permissions on CGI scripts...'
			for comp in self._comps:
				for filename in glob(comp['dirname'] + '/*.cgi'):
					cmd = 'chmod a+rx ' + filename
					self.printMsg(cmd)
					os.system(cmd)
			print 'Setting permission on start script...'
			cmd = 'chmod a+rx WebKit/webkit'
			self.printMsg(cmd)
			os.system(cmd)
			print

	def printGoodbye(self):
		print '''
Installation looks successful.

Welcome to Webware!

You can already try out the WebKit application server. Start it with
"WebKit%sAppServer" and point your browser to "http://localhost:8080".

Browsable documentation is available in the Docs folders.
You can use "Docs%sindex.html" as the main entry point.

Installation is finished.''' % ((os.sep,)*2)

	def writeLogFile(self, log):
		"""Write the logged output to the install.log file."""
		open('install.log', 'w').write(''.join(log))


	## Self utility ##

	def printKeyValue(self, key, value):
		"""Print a key/value pair."""
		value = value.split('\n')
		v = value.pop(0)
		print '%12s: %s' % (key, v)
		for v in value:
			print '%14s%s' % ('', v)

	def makeDir(self, dirName):
		"""Create a directory."""
		if not os.path.exists(dirName):
			self.printMsg('Making %s...' % dirName)
			os.makedirs(dirName)

	def htHeaderAndFooter(self):
		"""Return header and footer from HTML template."""
		template = open('Docs/Template.html').read()
		return template.split('\n<!-- page content -->\n', 1)

	def processHtmlDocFile(self, htmlFile):
		"""Process a HTML file."""
		txtFile = os.path.splitext(htmlFile)[0] + '.txt'
		if os.path.exists(txtFile):
			# A text file with the same name exists:
			page = open(htmlFile).read()
			if page.find('<meta name="generator" content="Docutils') > 0 \
				and page.find('<h1 class="title">') > 0:
				# This has obvisouly been created with Docutils; modify it
				# to match style, header and footer of all the other docs.
				page = page.replace('<h1 class="title">',
					'<h1 class="header">')
				page = page.replace('</body>\n</html>', self._htFooter)
				self.printMsg('Modifying %s...' % htmlFile)
				open(htmlFile, 'w').write(page)

	def processPyTemplateFile(self, inFile, props, keep):
		"""Process a Python template file."""
		page = open(inFile).read()
		page = self.processPyTemplate(page, props)
		outFile = os.path.splitext(inFile)[0] + '.html'
		self.printMsg('Creating %s...' % outFile)
		open(outFile, 'w').write(page)
		if not keep:
			os.remove(inFile) # remove template

	def processPyTemplate(self, input, props):
		"""Process a Python template."""
		global scope

		def header(title, titleclass=None, style=None):
			"""Get the header of a document."""
			if not titleclass:
				titleclass = 'header'
			titleclass = ' class="%s"' % titleclass
			link = '<link rel="stylesheet" href="%s" type="text/css">'
			stylesheets = ['Doc.css']
			if style and style.endswith('.css'):
				stylesheets.append(style)
				style = None
			css = []
			for s in stylesheets:
				if not scope['dirname'].startswith('.'):
					s = '../../Docs/' + s
				s = link % s
				css.append(s)
			if style:
				css.extend(('<style type="text/css">',
					'<!--', style, '-->', '</style>'))
			css = '\n'.join(css)
			return scope['htHeader'] % locals()

		def footer():
			"""Get the footer of a document."""
			return scope['htFooter']

		scope = props.copy()
		try:
			scope = dict(props)
		except NameError: # workaround for Python < 2.2
			scope = {}
			for k in props.keys():
				scope[k] = props[k]
		scope.update({'header': header, 'htHeader': self._htHeader,
				'footer': footer, 'htFooter': self._htFooter})
		return self._autotoc.process(self._pytp.process(input, scope))


def printHelp():
	print "Usage: install.py [options]"
	print "Install WebWare in the local directory."
	print
	print "  -h, --help            Print this help screen."
	print "  -v, --verbose         Print extra information messages during install."
	print "  --no-password-prompt  Don't prompt for WebKit password during install."
	print "  --set-password=...    Set the WebKit password to the given value."
	print "  --keep-templates      Keep the templates for creating the docs."


if __name__ == '__main__':
	import getopt
	verbose = 0
	passprompt = defaultpass = keepdocs = None
	try:
		opts, args = getopt.getopt(sys.argv[1:], "hv", ["help", "verbose",
			"no-password-prompt", "set-password=", "keep-templates"])
	except getopt.GetoptError:
		printHelp()
	else:
		for o, a in opts:
			if o in ("-v", "--verbose"):
				verbose = 1
			elif o == "--no-password-prompt":
				passprompt = 0
			elif o == "--set-password":
				defaultpass = a
			elif o == '--keep-templates':
				keepdocs = 1
			elif o in ("-h", "--help", "h", "help"):
				printHelp()
				sys.exit(0)
		if passprompt is None and defaultpass is None:
			passprompt = 1

		Installer().run(verbose=verbose, passprompt=passprompt,
			defaultpass=defaultpass, keepdocs=keepdocs)
