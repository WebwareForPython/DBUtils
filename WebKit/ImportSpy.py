"""ImportSpy

Keeps track of modules not imported directly by Webware for Python.

This module helps save the filepath of every module which is imported.
This is used by the `AutoReloadingAppServer` (see doc strings for more
information) to restart the server if any source files change.

Other than keeping track of the filepaths, the behaviour of this module
loader is identical to Python's default behaviour.

If the system supports FAM (file alteration monitor) and python-fam is
installed, then the need for reloading can be monitored very effectively
with the use of ImportSpy. Otherwise, ImportSpy will not have much benefit.

Note that ImportSpy is based on the new import hooks of Python 2.3 described in
PEP 302, falling back to the old ihooks module if new hooks are not available.
In some cases this may become problematic, when other templating systems are
used with Webware which are also using ihook support to load their templates,
or if they are using zipimports. Therefore, it is possible to suppress the use
of ImportSpy by setting `UseImportSpy` in AppServer.config to False.

"""


try: # if possible, use new (PEP 302) import hooks
	from sys import path_hooks, path_importer_cache
except ImportError:
	path_hooks = None


if path_hooks is not None:

	from os.path import isdir


	class ImportSpy(object):
		"""New style import tracker."""

		_imp = None

		def __init__(self, path=None):
			"""Create importer."""
			assert self._imp
			if path and isdir(path):
				self.path = path
			else:
				raise ImportError

		def find_module(self, fullname):
			"""Replaces imp.find_module."""
			try:
				self.file, self.filename, self.info = self._imp.find_module(
					fullname.split('.')[-1], [self.path])
			except ImportError:
				pass
			else:
				return self

		def load_module(self, fullname):
			"""Replaces imp.load_module."""
			mod = self._imp.load_module(fullname, self.file, self.filename, self.info)
			if mod:
				mod.__loader__ = self
			return mod

	def activate(impManager):
		"""Activate ImportSpy."""
		assert not ImportSpy._imp
		ImportSpy._imp = impManager
		path_hooks.append(ImportSpy)
		path_importer_cache.clear()
		impManager.recordModules()
		return 'new import hooks'


else: # Python < 2.3, fall back to using the old ihooks module

	import ihooks


	class ImportSpy(ihooks.ModuleLoader):
		"""Old style import tracker."""

		_imp = None

		def __init__(self):
			"""Create import hook."""
			assert self._imp
			ihooks.ModuleLoader.__init__(self)
			self._lock = self._imp._lock
			imp = ihooks.ModuleImporter(loader=self)
			ihooks.install(imp)
			self._imp.recordModules()

		def load_module(self, name, stuff):
			"""Replaces imp.load_module."""
			file, filename, info = stuff
			try:
				try:
					self._lock.acquire()
					mod = ihooks.ModuleLoader.load_module(self, name, stuff)
				finally:
					self._lock.release()
				self._imp.recordModule(mod)
			except:
				self._imp.recordFile(filename)
				raise
			return mod

	def activate(impManager):
		"""Activate ImportSpy."""
		assert not ImportSpy._imp
		ImportSpy._imp = impManager
		ImportSpy()
		return 'ihooks'
