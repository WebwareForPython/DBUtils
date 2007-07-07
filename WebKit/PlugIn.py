from Common import *
from MiscUtils.PropertiesObject import PropertiesObject


class PlugInError(Exception):
	pass


class PlugIn(Object):
	"""Template for Webware Plug-ins.

	A plug-in is a software component that is loaded by WebKit in order to
	provide additional WebKit functionality without necessarily having to modify
	WebKit's source. The most infamous plug-in is PSP (Python Server Pages)
	which ships with Webware.

	Plug-ins often provide additional servlet factories, servlet subclasses,
	examples and documentation. Ultimately, it is the plug-in author's choice
	as to what to provide and in what manner.

	Instances of this class represent plug-ins which are ultimately Python
	packages (see the Python Tutorial, 6.4: "Packages" at
	http://docs.python.org/tut/node8.html#SECTION008400000000000000000).

	A plug-in must also be a Webware component which means that it will have
	a Properties.py file advertising its name, version, requirements, etc.
	You can ask a plug-in for its properties().

	The plug-in/package must have an __init__.py while must contain a function:
		def InstallInWebKit(appServer):
	This function is invoked to take whatever actions are needed to plug the
	new component into WebKit. See PSP for an example.

	If you ask an AppServer for its plugIns(), you will get a list of instances
	of this class.

	The path of the plug-in is added to sys.path, if it's not already there.
	This is convenient, but we may need a more sophisticated solution in the
	future to avoid name collisions between plug-ins.

	Note that this class is hardly ever subclassed. The software in the
	plug-in package is what provides new functionality and there is currently
	no way to tell AppServer to use custom subclasses of this class on a
	case-by-case basis (and so far there is currently no need).

	Instructions for invoking:
		p = PlugIn(self, '../Foo') # 'self' is typically AppServer. It gets passed to InstallInWebKit()
		willNotLoadReason = plugIn.load()
		if willNotLoadReason:
			print '    Plug-in %s cannot be loaded because:\n    %s' % (path, willNotLoadReason)
			return None
		p.install()
		# Note that load() and install() could raise exceptions. You should expect this.

	"""


	## Init, load and install ##

	def __init__(self, appServer, path):
		"""Initializes the plug-in with basic information.

		This lightweight constructor does not access the file system.

		"""
		self._appServer = appServer
		self._path = path
		self._dir, self._name = os.path.split(path)
		self._cacheDir = os.path.join(
			self._appServer.application()._cacheDir, self._name)
		self._ver = '(unknown)'
		self._docs = self._docContext = None
		self._examplePages = self._examplePagesContext = None

	def load(self):
		"""Loads the plug-in into memory, but does not yet install it.

		Will return None on success, otherwise a message (string) that says
		why the plug-in could not be loaded.

		"""
		print 'Loading plug-in: %s at %s' % (self._name, self._path)

		assert os.path.exists(self._path)

		# Grab the Properties.py
		self._properties = PropertiesObject(self.serverSidePath('Properties.py'))
		if not self._properties['willRun']:
			return self._properties['willNotRunReason']

		# Update sys.path
		if not self._dir in sys.path:
			sys.path.append(self._dir)

		# Import the package
		self._module = __import__(self._name, globals(), [], [])

		# Inspect it and verify some required conventions
		if not hasattr(self._module, 'InstallInWebKit'):
			raise PlugInError, \
				"Plug-in '%s' in '%s' has no InstallInWebKit() function." \
				% (self._name, self._dir)

		# Give the module a pointer back to us
		setattr(self._module, 'plugIn', self)

		# Make a subdirectory for it in the Cache directory:
		if not os.path.exists(self._cacheDir):
			os.mkdir(self._cacheDir)

		self.setUpDocContext()
		self.setUpExamplePages()

	def setUpDocContext(self):
		"""Add a context for the documentation."""
		app = self._appServer.application()
		if app.hasContext('Docs'):
			self._docs = self._properties.get('docs', None) or None
			if self.hasDocs():
				docsPath = self.serverSidePath('Docs')
				assert os.path.exists(docsPath), \
					'Plug-in %s says it has documentation, ' \
					'but there is no Docs/ subdir.' % self._name
				if os.path.exists(os.path.join(docsPath, '__init__.py')):
					ctxName = self._name + '/Docs'
					if not app.hasContext(ctxName):
						app.addContext(ctxName, docsPath)
					self._docContext = ctxName
				else:
					print 'Cannot create Docs context for plug-in %s' \
						' (no __init__.py found).' % self._name

	def setUpExamplePages(self):
		"""Add a context for the examples."""
		app = self._appServer.application()
		if app.hasContext('Examples'):
			config = self._properties.get('WebKitConfig', {})
			self._examplePages = config.get('examplePages', None) or None
			if self.hasExamplePages():
				examplesPath = self.serverSidePath('Examples')
				assert os.path.exists(examplesPath), \
					'Plug-in %s says it has example pages, ' \
					'but there is no Examples/ subdir.' % self._name
				if os.path.exists(os.path.join(examplesPath, '__init__.py')):
					ctxName = self._name + '/Examples'
					if not app.hasContext(ctxName):
						app.addContext(ctxName, examplesPath)
					self._examplePagesContext = ctxName
				else:
					print 'Cannot create Examples context for plug-in %s' \
						' (no __init__.py found).' % self._name

	def docs(self):
		return self._docs

	def hasDocs(self):
		return self._docs is not None

	def docsContext(self):
		return self._docsContext

	def examplePages(self):
		return self._examplePages

	def hasExamplePages(self):
		return self._examplePages is not None

	def examplePagesContext(self):
		return self._examplePagesContext

	def install(self):
		"""Install plug-in by invoking its required InstallInWebKit function."""
		self._module.InstallInWebKit(self._appServer)


	## Access ##

	def name(self):
		"""Return the name of the plug-in. Example: 'Foo'"""
		return self._name

	def directory(self):
		"""Return the directory in which the plug-in resides. Example: '..'"""
		return self._dir

	def path(self):
		"""Return the full path of the plug-in. Example: '../Foo'"""
		return self._path

	def serverSidePath(self, path=None):
		if path:
			return os.path.normpath(os.path.join(self._path, path))
		else:
			return self._path

	def module(self):
		"""Return the Python module object of the plug-in."""
		return self._module

	def properties(self):
		"""Return the properties.

		This is a dictionary-like object, of the plug-in which comes
		from its Properties.py file. See MiscUtils.PropertiesObject.py.

		"""
		return self._properties
