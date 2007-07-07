from types import ClassType, BuiltinFunctionType
from keyword import iskeyword
import threading

from Common import *
from Servlet import Servlet

debug = False


class ServletFactory(Object):
	"""Servlet factory template.

	ServletFactory is an abstract class that defines the protocol for
	all servlet factories.

	Servlet factories are used by the Application to create servlets
	for transactions.

	A factory must inherit from this class and override uniqueness(),
	extensions() and either loadClass() or servletForTransaction().
	Do not invoke the base class methods as they all raise AbstractErrors.

	Each method is documented below.

	"""


	## Init ##

	def __init__(self, application):
		"""Create servlet factory.

		Stores a reference to the application in self._app, because
		subclasses may or may not need to talk back to the application
		to do their work.

		"""
		Object.__init__(self)
		self._app = application
		self._imp = self._app._imp
		self._cacheClasses = self._app.setting("CacheServletClasses", True)
		self._cacheInstances = self._app.setting("CacheServletInstances", True)
		# All caches are keyed on the path.
		# _classCache caches the servlet classes, in dictionaries
		# with keys 'mtime' and 'class'.  'mtime' is the
		# modification time of the enclosing module.
		self._classCache = {}
		# _servletPool has lists of free reusable servlets
		self._servletPool = {}
		# _threadsafeServletCache has threadsafe servlets
		# (which are not pooled, so only one is kept at a time)
		self._threadsafeServletCache = {}
		self._importLock = threading.RLock()


	## Info ##

	def name(self):
		"""Return the name of the factory.

		This is a convenience for the class name.

		"""
		return self.__class__.__name__

	def uniqueness(self):
		"""Return uniqueness type.

		Returns a string to indicate the uniqueness of the ServletFactory's
		servlets. The Application needs to know if the servlets are unique
		per file, per extension or per application.

		Return values are 'file', 'extension' and 'application'.

		NOTE: Application only supports 'file' uniqueness at this point in time.

		"""
		raise AbstractError, self.__class__

	def extensions(self):
		"""Return a list of extensions that match this handler.

		Extensions should include the dot. An empty string indicates a file
		with no extension and is a valid value. The extension '.*' is a special
		case that is looked for a URL's extension doesn't match anything.

		"""
		raise AbstractError, self.__class__


	## Import ##

	def importAsPackage(self, transaction, serverSidePathToImport):
		"""Import requested module.

		Imports the module at the given path in the proper package/subpackage
		for the current request. For example, if the transaction has the URL
		http://localhost/WebKit.cgi/MyContextDirectory/MySubdirectory/MyPage
		and path = 'some/random/path/MyModule.py' and the context is configured
		to have the name 'MyContext' then this function imports the module at
		that path as MyContext.MySubdirectory.MyModule . Note that the context
		name may differ from the name of the directory containing the context,
		even though they are usually the same by convention.

		Note that the module imported may have a different name from the
		servlet name specified in the URL. This is used in PSP.

		"""

		# Pull out the full server side path and the context path
		request = transaction.request()
		path = request.serverSidePath()
		contextPath = request.serverSideContextPath()
		fullname = request.contextName()

		# There is no context, so import the module standalone
		# and give it a unique name:
		if not fullname or not path.startswith(contextPath):
			remainder = serverSidePathToImport
			fullmodname = remainder.replace(
				'\\', '_').replace('/', '_').replace('.', '_')
			if debug:
				print __file__, ", fullmodname =", fullmodname
			modname = os.path.splitext(os.path.basename(
				serverSidePathToImport))[0]
			fp, pathname, stuff = self._imp.find_module(modname,
				[os.path.dirname(serverSidePathToImport)])
			module = self._imp.load_module(fullmodname, fp, pathname, stuff)
			module.__donotreload__ = True
			return module

		# First, we'll import the context's package.
		directory, contextDirName = os.path.split(contextPath)
		self._importModuleFromDirectory(fullname, contextDirName,
			directory, isPackageDir=True)
		directory = contextPath

		# Now we'll break up the rest of the path into components.
		remainder = path[len(contextPath)+1:].replace('\\', '/')
		remainder = remainder.split('/')

		# Import all subpackages of the context package
		for name in remainder[:-1]:
			fullname = '%s.%s' % (fullname, name)
			self._importModuleFromDirectory(fullname, name,
				directory, isPackageDir=True)
			directory = os.path.join(directory, name)

		# Finally, import the module itself as though it was part of the
		# package or subpackage, even though it may be located somewhere else.
		moduleFileName = os.path.basename(serverSidePathToImport)
		moduleDir = os.path.dirname(serverSidePathToImport)
		name = os.path.splitext(moduleFileName)[0]
		fullname = '%s.%s' % (fullname, name)
		module = self._importModuleFromDirectory(fullname, name,
			moduleDir, forceReload=True)
		return module

	def _importModuleFromDirectory(self, fullModuleName, moduleName,
			directory, isPackageDir=False, forceReload=False):
		"""Imports the given module from the given directory.

		fullModuleName should be the full dotted name that will be given
		to the module within Python. moduleName should be the name of the
		module in the filesystem, which may be different from the name
		given in fullModuleName. Returns the module object. If forceReload is
		True then this reloads the module even if it has already been imported.

		If isPackageDir is True, then this function creates an empty
		__init__.py if that file doesn't already exist.

		"""
		if debug:
			print __file__, fullModuleName, moduleName, directory
		if not forceReload:
			module = sys.modules.get(fullModuleName, None)
			if module is not None:
				return module
		fp = None
		if isPackageDir:
			# check if __init__.py is in the directory
			packageDir = os.path.join(directory, moduleName)
			initPy = os.path.join(packageDir, '__init__.py')
			if not os.path.exists(initPy):
				# if it does not exist, make an empty one
				file = open(initPy, 'w')
				file.write('#')
				file.close()
		fp, pathname, stuff = self._imp.find_module(moduleName, [directory])
		module = self._imp.load_module(fullModuleName, fp, pathname, stuff)
		module.__donotreload__ = True
		return module

	def loadClass(self, transaction, path):
		"""Load the appropriate class.

		Given a transaction and a path, load the class for creating these
		servlets. Caching, pooling, and threadsafeness are all handled by
		servletForTransaction. This method is not expected to be threadsafe.

		"""
		raise AbstractError, self.__class__


	## Servlet Pool ##

	def servletForTransaction(self, transaction):
		"""Return a new servlet that will handle the transaction.

		This method handles caching, and will call loadClass(trans, filepath)
		if no cache is found. Caching is generally controlled by servlets
		with the canBeReused() and canBeThreaded() methods.

		"""
		request = transaction.request()
		path = request.serverSidePath()
		# Do we need to import/reimport the class
		# because the file changed on disk or isn't in cache?
		mtime = os.path.getmtime(path)
		if not self._classCache.has_key(path) or \
				mtime != self._classCache[path]['mtime']:
			# Use a lock to prevent multiple simultaneous
			# imports of the same module:
			self._importLock.acquire()
			try:
				if not self._classCache.has_key(path) or \
						mtime != self._classCache[path]['mtime']:
					theClass = self.loadClass(transaction, path)
					if self._cacheClasses:
						self._classCache[path] = {
							'mtime': mtime, 'class': theClass}
				else:
					theClass = self._classCache[path]['class']
			finally:
				self._importLock.release()
		else:
			theClass = self._classCache[path]['class']

		# Try to find a cached servlet of the correct class.
		# (Outdated servlets may have been returned to the pool after a new
		# class was imported, but we don't want to use an outdated servlet.)
		if self._threadsafeServletCache.has_key(path):
			servlet = self._threadsafeServletCache[path]
			if servlet.__class__ is theClass:
				return servlet
		else:
			while 1:
				try:
					servlet = self._servletPool[path].pop()
				except (KeyError, IndexError):
					break
				else:
					if servlet.__class__ is theClass:
						servlet.open()
						return servlet

		# Use a lock to prevent multiple simultaneous imports of the same
		# module. Note that (only) the import itself is already threadsafe.
		self._importLock.acquire()
		try:
			mtime = os.path.getmtime(path)
			if not self._classCache.has_key(path):
				self._classCache[path] = {
					'mtime': mtime,
					'class': self.loadClass(transaction, path)}
			elif mtime > self._classCache[path]['mtime']:
				self._classCache[path]['mtime'] = mtime
				self._classCache[path]['class'] = self.loadClass(
					transaction, path)
			theClass = self._classCache[path]['class']
			if not self._cacheClasses:
				del self._classCache[path]
		finally:
			self._importLock.release()

		# No adequate cached servlet exists, so create a new servlet instance
		servlet = theClass()
		servlet.setFactory(self)
		if servlet.canBeReused():
			if servlet.canBeThreaded():
				self._threadsafeServletCache[path] = servlet
			else:
				self._servletPool[path] = []
				servlet.open()
		return servlet

	def returnServlet(self, servlet):
		"""Return servlet to the pool.

		Called by Servlet.close(), which returns the servlet
		to the servlet pool if necessary.

		"""
		if servlet.canBeReused() and not servlet.canBeThreaded() \
				and self._cacheInstances:
			path = servlet.serverSidePath()
			self._servletPool[path].append(servlet)

	def flushCache(self):
		"""Flush the servlet cache and start fresh.

		Servlets that are currently in the wild may find their way back
		into the cache (this may be a problem).

		"""
		# @@ ib 07-2003: I'm unsure how well this works.
		self._importLock.acquire()
		self._classCache = {}
		# We can't just delete all the lists, because returning
		# servlets expect it to exist.
		for key in self._servletPool.keys():
			self._servletPool[key] = []
		self._threadsafeServletCache = {}
		self._importLock.release()


class PythonServletFactory(ServletFactory):
	"""The factory for Python servlets.

	This is the factory for ordinary Python servlets whose extensions
	are empty or .py. The servlets are unique per file since the file
	itself defines the servlet.

	"""


	## Info ##

	def uniqueness(self):
		return 'file'

	def extensions(self):
		# The extensions of ordinary Python servlets. Besides .py, we also
		# allow .pyc and .pyo files as Python servlets, so you can use
		# servlets in the production environment without the source code.
		# Otherwise they would be treated as ordinary files which might
		# become a security hole (though the standard configuration ignores
		# the .pyc and .pyo files). If you use all of them, make sure .py
		# comes before .pyc and .pyo in the ExtensionCascadeOrder.
		return ['.py', '.pyc', '.pyo']


	## Import ##

	def loadClass(self, transaction, path):
		# Import the module as part of the context's package
		module = self.importAsPackage(transaction, path)

		# The class name is expected to be the same as the servlet name:
		name = os.path.splitext(os.path.split(path)[1])[0]
		# Check whether such a class exists in the servlet module:
		if not hasattr(module, name):
			# If it does not exist, maybe the name has to be mangled.
			# Servlet names may have dashes or blanks in them, but classes not.
			# So we automatically translate dashes blanks to underscores:
			name = name.replace('-', '_').replace(' ', '_')
			# You may also have a servlet name that is a Python reserved word.
			# Automatically append an underscore in these cases:
			if iskeyword(name):
				name += '_'
			# If the mangled name does not exist either, report an error:
			if not hasattr(module, name):
				raise ValueError, \
					'Cannot find expected servlet class %r in %r.' \
						% (name, path)
		# Pull the servlet class out of the module:
		theClass = getattr(module, name)

		# New-style classes aren't ClassType, but they are okay to use.
		# They are subclasses of type. But type isn't a class in older
		# Python versions, it's a builtin function. So we test what type
		# is first, then use isinstance only for the newer Python versions.
		if type(type) is BuiltinFunctionType:
			assert type(theClass) is ClassType
		else:
			assert type(theClass) is ClassType \
				or isinstance(theClass, type)
		assert issubclass(theClass, Servlet)
		return theClass
