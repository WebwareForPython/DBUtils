import os, sys
from types import ClassType, DictType

try:
	from cPickle import load, dump
except ImportError:
	from pickle import load, dump

from MiscUtils.Configurable import Configurable
from MiscUtils import NoDefault

try: # for Python < 2.3
	True, False
except NameError:
	True, False = 1, 0


class ModelError(Exception):

	def __init__(self, error, line=None):
		self._line = line
		self._error = error
		if line is not None:
			args = (line, error)
		else:
			args = (error,)
		Exception.__init__(self, *args)

	def setLine(self, line):
		self._line = line

	def printError(self, filename):
		self.args = (filename,) + self.args
		if self._line:
			print '%s:%d: %s' % (filename, self._line, self._error)
		else:
			print '%s: %s' % (filename, self._error)


class Model(Configurable):
	"""A Model defines the classes, attributes and enumerations of an application.

	It also provides access to the Python classes that implement these structures
	for use by other MiddleKit entities including code generators and object stores.

	"""

	pickleVersion = 1
		# increment this if a non-compatible change is made in Klasses,
		# Klass or Attr

	def __init__(self,
			filename=None, classesFilename=None, configFilename=None,
			customCoreClasses={}, rootModel=None, havePythonClasses=1):
		Configurable.__init__(self)
		self._havePythonClasses = havePythonClasses
		self._filename = None
		self._configFilename = configFilename or 'Settings.config'
		self._coreClasses = customCoreClasses
		self._klasses = None
		self._name = None
		self._parents = []  # e.g., parent models
		self._pyClassForName = {}

		# _allModelsByFilename is used to avoid loading the same parent model twice
		if rootModel:
			self._allModelsByFilename = rootModel._allModelsByFilename
		else:
			self._allModelsByFilename = {}
		self._rootModel = rootModel

		if filename or classesFilename:
			self.read(filename or classesFilename, classesFilename is not None)

	def name(self):
		if self._name is None:
			if self._filename:
				self._name = os.path.splitext(os.path.basename(self._filename))[0]
			else:
				self._name = 'unnamed-mk-model'
		return self._name

	def setName(self, name):
		self._name = name

	def filename(self):
		return self._filename

	def read(self, filename, isClassesFile=0):
		import time
		start = time.time()
		assert self._filename is None, 'Cannot read twice.'
		# Assume the .mkmodel extension if none is given
		if os.path.splitext(filename)[1] == '':
			filename += '.mkmodel'
		self._filename = os.path.abspath(filename)
		self._name = None
		if isClassesFile:
			self.dontReadParents()
		else:
			self.readParents()  # the norm
		try:
			if isClassesFile:
				self.readKlassesDirectly(filename)
			else:
				self.readKlassesInModelDir()  # the norm
			self.awakeFromRead()
		except ModelError, e:
			print
			print 'Error while reading model:'
			e.printError(filename)
			raise
			#sys.exit(1)
		dur = time.time() - start
		# print '%.2f seconds\n' % dur

	def readKlassesInModelDir(self):
		"""Read the Classes.csv or Classes.pickle.cache file as appropriate."""
		path = None
		csvPath = os.path.join(self._filename, 'Classes.csv')
		if os.path.exists(csvPath):
			path = csvPath
		xlPath = os.path.join(self._filename, 'Classes.xls')
		if os.path.exists(xlPath):
			path = xlPath
		if path is None:
			open(csvPath) # to get a properly constructed IOError

		self.readKlassesDirectly(path)

	def readKlassesDirectly(self, path):
		# read the pickled version of Classes if possible
		data = None
		shouldUseCache = self.setting('UsePickledClassesCache', 0)
		if shouldUseCache:
			from MiscUtils.PickleCache import readPickleCache, writePickleCache
			data = readPickleCache(path, pickleVersion=1, source='MiddleKit')

		# read the regular file if necessary
		if data is None:
			self.klasses().read(path)
			if shouldUseCache:
				writePickleCache(self._klasses, path, pickleVersion=1, source='MiddleKit')
		else:
			self._klasses = data
			self._klasses._model = self

	def __getstate__(self):
		raise Exception, 'Model instances were not designed to be pickled.'

	def awakeFromRead(self):
		# create containers for all klasses, uniqued by name
		models = list(self._searchOrder)
		models.reverse()
		byName = {}
		inOrder = []
		for model in models:
			for klass in model.klasses().klassesInOrder():
				name = klass.name()
				if byName.has_key(name):
					for i in range(len(inOrder)):
						if inOrder[i].name() == name:
							inOrder[i] = klass
				else:
					inOrder.append(klass)
				byName[name] = klass
		assert len(byName) == len(inOrder)
		for name, klass in byName.items():
			assert klass is self.klass(name)
		for klass in inOrder:
			assert klass is self.klass(klass.name())
		self._allKlassesByName = byName
		self._allKlassesInOrder = inOrder

		self._klasses.awakeFromRead(self)


	def readParents(self, parentFilenames=None):
		"""
		Reads the parent models of the current model, as
		specified in the 'Inherit' setting.

		The attributes _parents and _searchOrder are set.
		"""
		if parentFilenames is None:
			parentFilenames = self.setting('Inherit', [])
		for filename in parentFilenames:
			filename = os.path.abspath(os.path.join(
				os.path.dirname(self._filename), filename))
			if self._allModelsByFilename.has_key(filename):
				model = self._allModelsByFilename[filename]
				assert model != self._rootModel
			else:
				model = self.__class__(filename,
					customCoreClasses=self._coreClasses,
					rootModel=self, havePythonClasses=self._havePythonClasses)
				self._allModelsByFilename[filename] = model
			self._parents.append(model)

		# establish the search order
		# algorithm taken from http://www.python.org/2.2/descrintro.html#mro
		searchOrder = self.allModelsDepthFirstLeftRight()

		# remove duplicates:
		indexes = range(len(searchOrder))
		indexes.reverse()
		for i in indexes:
			if i < len(searchOrder):
				model = searchOrder[i]
				j = 0
				while j < i:
					if searchOrder[j] is model:
						del searchOrder[j]
						i -= 1
					else:
						j += 1

		self._searchOrder = searchOrder

	def dontReadParents(self):
		"""Set attributes _parents and _searchOrder.

		Used internally for the rare case of reading class files directly
		(instead of from a model directory).

		"""
		self._parents = []
		self._searchOrder = [self]

	def allModelsDepthFirstLeftRight(self, parents=None):
		"""Return ordered list of models.

		Returns a list of all models, including self, parents and
		ancestors, in a depth-first, left-to-right order. Does not
		remove duplicates (found in inheritance diamonds).

		Mostly useful for readParents() to establish the lookup
		order regarding model inheritance.

		"""
		if parents is None:
			parents = []
		parents.append(self)
		for parent in self._parents:
			parent.allModelsDepthFirstLeftRight(parents)
		return parents

	def coreClass(self, className):
		"""Return code class.

		For the given name, returns a class from MiddleKit.Core
		or the custom set of classes that were passed in via initialization.

		"""
		pyClass = self._coreClasses.get(className, None)
		if pyClass is None:
			results = {}
			exec 'import MiddleKit.Core.%s as module'%className in results
			pyClass = getattr(results['module'], className)
			assert type(pyClass) is ClassType
			self._coreClasses[className] = pyClass
		return pyClass

	def coreClassNames(self):
		"""Return a list of model class names found in MiddleKit.Core."""
		# a little cheesy, but it does the job:
		import MiddleKit.Core as Core
		return Core.__all__

	def klasses(self):
		"""Get klasses.

		Returns an instance that inherits from Klasses, using the base
		classes passed to __init__, if any.

		See also: klass(), allKlassesInOrder(), allKlassesByName()

		"""
		if self._klasses is None:
			Klasses = self.coreClass('Klasses')
			self._klasses = Klasses(self)
		return self._klasses

	def klass(self, name, default=NoDefault):
		"""Get klass.

		Returns the klass with the given name, searching the parent
		models if necessary.

		"""
		for model in self._searchOrder:
			klass = model.klasses().get(name, None)
			if klass:
				return klass
		if default is NoDefault:
			raise KeyError, name
		else:
			return default

	def allKlassesInOrder(self):
		"""Get klasses in order.

		Returns a sequence of all the klasses in this model, unique by
		name, including klasses inherited from parent models.

		The order is the order of declaration, top-down.

		"""
		return self._allKlassesInOrder

	def allKlassesByName(self):
		"""Get klasses by name.

		Returns a dictionary of all the klasses in this model, unique
		by name, including klasses inherited from parent models.

		"""
		return self._allKlassesByName

	def allKlassesInDependencyOrder(self):
		"""Get klasses in dependency order.

		Returns a sequence of all the klasses in this model, in an
		order such that klasses follow the klasses they refer to
		(via obj ref attributes).
		The typical use for such an order is to avoid SQL errors
		about foreign keys referring to tables that do not exist.

		A ModelError is raised if there is a dependency cycle
		since there can be no definitive order when a cycle exists.
		You can break cycles by setting Ref=False for some
		attribute in the cycle.

		"""
		for klass in self._allKlassesInOrder:
			klass.willBuildDependencies()
		for klass in self._allKlassesInOrder:
			klass.buildDependencies()
		allKlasses = []
		visited = {} # better use Set() in Python 2.3 and set() in Python >= 2.4
		for klass in self._allKlassesInOrder:
			if not klass._dependents:
				# print '>>', klass.name()
				klass.recordDependencyOrder(allKlasses, visited)
		# The above loop fails to capture classes that are in cycles,
		# but in that case there really is no dependency order.
		if len(allKlasses) < len(self._allKlassesInOrder):
			raise ModelError("Cannot determine a dependency order"
				" among the classes due to a cycle. Try setting Ref=0"
				" for one of the attributes to break the cycle.")
		assert len(allKlasses) == len(self._allKlassesInOrder), \
			'%r, %r, %r' % (len(allKlasses), len(self._allKlassesInOrder), allKlasses)
		# print '>> allKlassesInDependencyOrder() =', ' '.join([k.name() for k in allKlasses])
		return allKlasses

	def pyClassForName(self, name):
		"""Get Python class for name.

		Returns the Python class for the given name, which must be present
		in the object model. Accounts for self.setting('Package').

		If you already have a reference to the model klass, then you can
		just ask it for klass.pyClass().

		"""
		pyClass = self._pyClassForName.get(name, None)
		if pyClass is None:
			results = {}
			pkg = self.setting('Package', '')
			if pkg:
				pkg += '.'
			try:
				exec 'import %s%s as module' % (pkg, name) in results
			except ImportError, exc:
				raise ModelError("Could not import module for class '%s' due to %r."
					" If you've added this class recently,"
					" you need to re-generate your model." % (name, exc.args[0]))
			pyClass = getattr(results['module'], 'pyClass', None)
			if pyClass is None:
				pyClass = getattr(results['module'], name)
			# Note: The 'pyClass' variable name that is first looked for is a hook for
			# those modules that have replaced the class variable by something else,
			# like a function. I did this in a project with a class called UniqueString()
			# in order to guarantee uniqueness per string.
			self._pyClassForName[name] = pyClass
		return pyClass


	## Being configurable ##

	def configFilename(self):
		if self._filename is None:
			return None
		else:
			return os.path.join(self._filename, self._configFilename)

	def defaultConfig(self):
		return {
			'Threaded': True,
			'ObjRefSuffixes': ('ClassId', 'ObjId'),
			'UseBigIntObjRefColumns': False,
			# 'SQLLog': { 'File': 'stdout', },
			'PreSQL': '',
			'PostSQL': '',
			'DropStatements': 'database',  # database, tables
			'SQLSerialColumnName': 'serialNum',  # can use [cC]lassName, _ClassName
			'AccessorStyle': 'methods',  # can be 'methods' or 'properties'
			'ExternalEnumsSQLNames': {
				'Enable': False,
				'TableName': '%(ClassName)s%(AttrName)sEnum',
				'ValueColName': 'value',
				'NameColName': 'name',
			},
			# can use: [cC]lassName, _ClassName, [aA]ttrName, _AttrName.
			# "_" prefix means "as is", the others control the case of the first character.
		}

	def usesExternalSQLEnums(self):
		flag = getattr(self, '_usesExternalSQLEnums', None)
		if flag is None:
			flag = self.setting('ExternalEnumsSQLNames')['Enable']
			self._usesExternalSQLEnums = flag
		return flag


	## Warnings ##

	def printWarnings(self, out=None):
		if out is None:
			out = sys.stdout
		if len(self._klasses.klassesInOrder()) < 1:
			out.write("warning: Model '%s' doesn't contain any class definitions.\n"
				% self.name())
		for klass in self.klasses().klassesInOrder():
			klass.printWarnings(out)
