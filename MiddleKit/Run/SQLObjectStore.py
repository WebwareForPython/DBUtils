import sys, time, types


from MiddleObject import MiddleObject
from ObjectStore import ObjectStore, UnknownObjectError
from ObjectKey import ObjectKey
from MiddleKit.Core.ObjRefAttr import objRefJoin, objRefSplit
from MiscUtils import NoDefault, StringTypes, AbstractError, CSVJoiner
from MiscUtils import Funcs as funcs
from MiscUtils.DBPool import DBPool
from MiscUtils.MixIn import MixIn

try: # for Python < 2.3
	True, False
except NameError:
	True, False = 1, 0

class SQLObjectStoreError(Exception): pass
class SQLObjectStoreThreadingError(SQLObjectStoreError): pass
class ObjRefError(SQLObjectStoreError): pass
class ObjRefZeroSerialNumError(ObjRefError): pass
class ObjRefDanglesError(ObjRefError): pass


aggressiveGC = False


class UnknownSerialNumberError(SQLObjectStoreError):
	"""
	For internal use when archiving objects.

	Sometimes an obj ref cannot be immediately resolved on INSERT because
	the target has not yet been inserted and therefore, given a serial number.
	"""

	def __init__(self, info):
		self.info = info

	def __repr__(self):
		return '%s: %s' % (self.__class__.__name__, self.info)

	def __str__(self):
		return str(self.info)


class UnknownSerialNumInfo:
	"""
	Attrs assigned externally are:
		sourceObject
		sourceAttr
		targetObject
	"""

	def updateStmt(self):
		assert self.sourceObject.serialNum != 0
		assert self.targetObject.serialNum() != 0
		sourceKlass = self.sourceObject._mk_klass
		assert sourceKlass
		sourceTableName = sourceKlass.sqlTableName()
		sourceSqlSerialName = sourceKlass.sqlSerialColumnName()
		return 'update %s set %s where %s=%s;' % (
			sourceTableName, self.sourceAttr.sqlUpdateExpr(self.targetObject), sourceSqlSerialName, self.sourceObject.serialNum())

	def __repr__(self):
		s = []
		for item in self.__dict__.items():
			s.append('%s=%r' % item)
		s = ' '.join(s)
		return '<%s %s>' % (self.__class__.__name__, s)


class SQLObjectStore(ObjectStore):
	"""
	TO DO:

		* _sqlEcho should be accessible via a config file setting as stdout, stderr or a filename.

	For details on DB API 2.0, including the thread safety levels see:
		http://www.python.org/topics/database/DatabaseAPI-2.0.html
	"""


	## Init ##

	def __init__(self, **kwargs):
		# @@ 2001-02-12 ce: We probably need a dictionary before kwargs for subclasses to pass to us in case they override __init__() and end up collecting kwargs themselves

		ObjectStore.__init__(self)
		self._dbArgs = kwargs
		self._connected = False
		self._commited = False
		self._sqlEcho   = None
		self._sqlCount  = 0
		self._pool = None   # an optional DBPool

	def modelWasSet(self):
		"""
		Performs additional set up of the store after the model is set,
		normally via setModel() or readModelFileNamed(). This includes
		checking that threading conditions are valid, and connecting to
		the database.
		"""
		ObjectStore.modelWasSet(self)

		# Check thread safety
		self._threadSafety = self.threadSafety()
		if self._threaded and self._threadSafety == 0:
			raise SQLObjectStoreThreadingError, 'Threaded is True, but the DB API threadsafety is 0.'

		# Cache some settings
		self._markDeletes = self.setting('DeleteBehavior', 'delete') == 'mark'

		# Set up SQL echo
		self.setUpSQLEcho()

		# Set up attrs for caching
		for klass in self.model().allKlassesInOrder():
			klass._getMethods = {}
			klass._setMethods = {}
			for attr in klass.allDataAttrs():
				attr._sqlColumnName = None
				attr._sqlColumnNames = None

		# use dbargs from settings file as defaults
		# (args passed to __init__ take precedence)
		args = self._dbArgs
		self._dbArgs = self.setting('DatabaseArgs', {})
		self._dbArgs.update(args)
		# print 'dbArgs = %s' % self._dbArgs

		# Connect
		self.connect()


	def setUpSQLEcho(self):
		"""
		Sets up the SQL echoing/logging for the store according to the
		setting 'SQLLog'. See the User's Guide for more info. Invoked by
		modelWasSet().
		"""
		setting = self.setting('SQLLog', None)
		if setting is None or setting == {}:
			self._sqlEcho = None
		else:
			filename = setting['File']
			if filename is None:
				self._sqlEcho = None
			elif filename == 'stdout':
				self._sqlEcho = sys.stdout
			elif filename == 'stderr':
				self._sqlEcho = sys.stderr
			else:
				mode = setting.get('Mode', 'write')
				assert mode in ['write', 'append']
				mode = mode[0]
				self._sqlEcho = open(filename, mode)


	## Connecting to the db ##

	def isConnected(self):
		return self._connected

	def connect(self):
		"""
		Connects to the database only if the store has not already and
		provided that the store has a valid model.

		The default implementation of connect() is usually sufficient
		provided that subclasses have implemented newConnection().
		"""
		assert self._model, 'Cannot connect: No model has been attached to this store yet.'
		if not self._connected:
			self._connection = self.newConnection()
			self._connected = True
			self.readKlassIds()
			poolSize = self.setting('SQLConnectionPoolSize', 0)
			if poolSize:
				args = self._dbArgs.copy()
				self.augmentDatabaseArgs(args, pool=1)
				try:
					self._pool = DBPool(self.dbapiModule(), poolSize, **args)
				except TypeError:
					if args.has_key('database'):
						del args['database']
						self._pool = DBPool(self.dbapiModule(), poolSize, **args)
					else:
						raise

	def augmentDatabaseArgs(self, args, pool=0):
		# give subclasses the opportunity to add or change
		# database arguments
		pass

	def newConnection(self):
		"""
		Returns a DB API 2.0 connection. This is a utility method
		invoked by connect(). Subclasses should implement this, making
		use of self._dbArgs (a dictionary specifying host, username,
		etc.) as well as self._model.sqlDatabaseName().

		Subclass responsibility.
		"""
		raise AbstractError, self.__class__

	def readKlassIds(self):
		"""
		Reads the klass ids from the SQL database. Invoked by connect().
		"""
		conn, cur = self.executeSQL('select id, name from _MKClassIds;')
		try:
			klassesById = {}
			for (id, name) in cur.fetchall():
				assert id, "Id must be a non-zero int. id=%r, name=%r" % (id, name)
				try:
					klass = self._model.klass(name)
				except KeyError:
					filename = self._model.filename()
					msg = '%s  The database has a class id for %r in the _MKClassIds table, but no such class exists in the model %s. The model and the db are not in sync.' % (name, name, filename)
					raise KeyError, msg
				klassesById[id] = klass
				klass.setId(id)
		finally:
			self.doneWithConnection(conn)
		self._klassesById = klassesById


	## Changes ##

	def commitInserts(self, allThreads=False):
		unknownSerialNums = []
		# @@ ... sort here for dependency order
		for object in self._newObjects.items(allThreads):
			self._insertObject(object, unknownSerialNums)

		conn = None
		try:
			for unknownInfo in unknownSerialNums:
				stmt = unknownInfo.updateStmt()
				conn, cur = self.executeSQL(stmt, conn)
		finally:
			self.doneWithConnection(conn)
		self._newObjects.clear(allThreads)

	def _insertObject(self, object, unknownSerialNums):
		# New objects not in the persistent store have serial numbers less than 1
		if object.serialNum() > 0:
			try:
				rep = repr(object)
			except:
				rep = '(repr exception)'
			assert object.serialNum() < 1, 'object=%s' % rep

		# try to get the next ID (if database supports this)
		idNum = self.retrieveNextInsertId(object.klass())

		# SQL insert
		sql = object.sqlInsertStmt(unknownSerialNums, idNum)
		conn, cur = self.executeSQL(sql)
		try:
			# Get new id/serial num
			if idNum is None:
				idNum = self.retrieveLastInsertId(conn, cur)

			# Update object
			object.setSerialNum(idNum)
			object.setKey(ObjectKey().initFromObject(object))
			object.setChanged(False)

			# Update our object pool
			self._objects[object.key()] = object
		finally:
			self.doneWithConnection(conn)

	def retrieveNextInsertId(self, klass):
		""" Returns the id for the next new object of this class.  Databases which cannot determine
		the id until the object has been added return None, signifying that retrieveLastInsertId
		should be called to get the id after the insert has been made. """
		return None

	def retrieveLastInsertId(self, conn, cur):
		""" Returns the id (typically a 32-bit int) of the last INSERT operation by this connection. Used by commitInserts() to get the correct serial number for the last inserted object.
		Subclass responsibility. """
		raise AbstractError, self.__class__

	def commitUpdates(self, allThreads=False):
		conn = None
		try:
			for object in self._changedObjects.values(allThreads):
				sql = object.sqlUpdateStmt()
				conn, cur = self.executeSQL(sql, conn)
				object.setChanged(False)
		finally:
			self.doneWithConnection(conn)
		self._changedObjects.clear(allThreads)

	def commitDeletions(self, allThreads=False):
		conn = None
		try:
			for object in self._deletedObjects.items(allThreads):
				sql = object.sqlDeleteStmt()
				conn, cur = self.executeSQL(sql, conn)
		finally:
			self.doneWithConnection(conn)
		self._deletedObjects.clear(allThreads)


	## Fetching ##

	def fetchObject(self, aClass, serialNum, default=NoDefault):
		""" Fetches a single object of a specific class and serial number. TheClass can be a Klass object (from the MiddleKit object model), the name of the class (e.g., a string) or a Python class.
		Raises an exception if theClass parameter is invalid, or the object cannot be located.
		"""
		klass = self._klassForClass(aClass)
		objects = self.fetchObjectsOfClass(klass, serialNum=serialNum, isDeep=False)
		count = len(objects)
		if count == 0:
			if default is NoDefault:
				raise UnknownObjectError, 'aClass = %r, serialNum = %r' % (aClass, serialNum)
			else:
				return default
		else:
			assert count == 1
			return objects[0]

	def fetchObjectsOfClass(self, aClass, clauses='', isDeep=True, refreshAttrs=True, serialNum=None):
		"""
		Fetches a list of objects of a specific class. The list may be empty if no objects are found.
		aClass can be a Klass object (from the MiddleKit object model), the name of the class (e.g., a string) or a Python class.
		The clauses argument can be any SQL clauses such as 'where x<5 order by x'. Obviously, these could be specific to your SQL database, thereby making your code non-portable. Use your best judgement.
		serialNum can be a specific serial number if you are looking for a specific object.  If serialNum is provided, it overrides the clauses.
		You should label all arguments other than aClass:
			objs = store.fetchObjectsOfClass('Foo', clauses='where x<5')
		The reason for labeling is that this method is likely to undergo improvements in the future which could include additional arguments. No guarantees are made about the order of the arguments except that aClass will always be the first.
		Raises an exception if aClass parameter is invalid.
		"""
		klass = self._klassForClass(aClass)

		# Fetch objects of subclasses first, because the code below will be modifying clauses and serialNum
		deepObjs = []
		if isDeep:
			for subklass in klass.subklasses():
				deepObjs.extend(self.fetchObjectsOfClass(subklass, clauses, isDeep, refreshAttrs, serialNum))

		# Now get objects of this exact class
		objs = []
		if not klass.isAbstract():
			fetchSQLStart = klass.fetchSQLStart()
			className = klass.name()
			if serialNum is not None:
				serialNum = int(serialNum)  # make sure it's a valid int (suppose it came in as a string: 'foo')
				clauses = 'where %s=%d' % (klass.sqlSerialColumnName(), serialNum)
			if self._markDeletes:
				clauses = self.addDeletedToClauses(clauses)
			conn, cur = self.executeSQL(fetchSQLStart + clauses + ';')
			try:
				for row in cur.fetchall():
					serialNum = row[0]
					key = ObjectKey().initFromClassNameAndSerialNum(className, serialNum)
					obj = self._objects.get(key, None)
					if obj is None:
						pyClass = klass.pyClass()
						obj = pyClass()
						assert isinstance(obj, MiddleObject), 'Not a MiddleObject. obj = %r, type = %r, MiddleObject = %r' % (obj, type(obj), MiddleObject)
						obj.readStoreData(self, row)
						obj.setKey(key)
						self._objects[key] = obj
					else:
						# Existing object
						if refreshAttrs:
							obj.readStoreData(self, row)
					objs.append(obj)
			finally:
				self.doneWithConnection(conn)
		objs.extend(deepObjs)
		return objs

	def refreshObject(self, obj):
		assert obj.store() is self
		return self.fetchObject(obj.klass(), obj.serialNum())


	## Klasses ##

	def klassForId(self, id):
		return self._klassesById[id]


	## Self utility for SQL, connections, cursors, etc. ##

	def executeSQL(self, sql, connection=None):
		"""
		Executes the given SQL, connecting to the database for the first
		time if necessary. This method will also log the SQL to
		self._sqlEcho, if it is not None. Returns the connection and
		cursor used and relies on connectionAndCursor() to obtain these.
		Note that you can pass in a connection to force a particular one
		to be used.
		"""
		sql = str(sql) # Excel-based models yield Unicode strings which some db modules don't like
		sql = sql.strip()
		if aggressiveGC:
			import gc
			assert gc.isenabled()
			gc.collect()
		self._sqlCount += 1
		if self._sqlEcho:
			timestamp = funcs.timestamp()['pretty']
			self._sqlEcho.write('SQL %04i. %s %s\n' % (self._sqlCount, timestamp, sql))
			self._sqlEcho.flush()
		conn, cur = self.connectionAndCursor(connection)
		self._executeSQL(cur, sql)
		return conn, cur

	def _executeSQL(self, cur, sql):
		"""
		Invokes execute on the cursor with the given SQL. This is a
		hook for subclasses that wish to influence this event. Invoked
		by executeSQL().
		"""
		cur.execute(sql)

	def setSQLEcho(self, file):
		""" Sets a file to echo sql statements to, as sent through executeSQL(). None can be passed to turn echo off. """
		self._sqlEcho = file

	def connectionAndCursor(self, connection=None):
		"""
		Returns the connection and cursor needed for executing SQL,
		taking into account factors such as setting('Threaded') and the
		threadsafety level of the DB API module. You can pass in a
		connection to force a particular one to be used. Uses
		newConnection() and connect().
		"""
		if aggressiveGC:
			import gc
			assert gc.isenabled()
			gc.collect()
		if connection:
			conn = connection
		elif self._threaded:
			if self._pool:
				conn = self._pool.connection()
			elif self._threadSafety == 1:
				conn = self.newConnection()
			else: # safety = 2, 3
				if not self._connected:
					self.connect()
				conn = self._connection
		else:
			# Non-threaded
			if not self._connected:
				self.connect()
			conn = self._connection
		cursor = conn.cursor()
		return conn, cursor

	def newConnection(self):
		"""
		Subclasses must override to return a newly created database connection.
		"""
		raise AbstractError, self.__class__

	def threadSafety(self):
		return self.dbapiModule().threadsafety

	def addDeletedToClauses(self, clauses):
		"""
		Modify the given set of clauses so that it filters out records with non-NULL deleted field
		"""
		clauses = clauses.strip()
		if clauses.lower().startswith('where'):
			orderByIndex = clauses.lower().find('order by')
			if orderByIndex == -1:
				where = clauses[5:]
				orderBy = ''
			else:
				where = clauses[5:orderByIndex]
				orderBy = clauses[orderByIndex:]
			return 'where deleted is null and (%s) %s' % (where, orderBy)
		else:
			return 'where deleted is null %s' % clauses


	## Obj refs ##

	def fetchObjRef(self, objRef):
		"""
		Given an unarchived object reference, this method returns the
		actual object for it (or None if the reference is NULL or
		dangling). While this method assumes that obj refs are stored
		as 64-bit numbers containing the class id and object serial
		number, subclasses are certainly able to override that
		assumption by overriding this method.
		"""
		assert isinstance(objRef, types.LongType), 'type=%r, objRef=%r' % (type(objRef), objRef)
		if objRef == 0:
			return None
		else:
			klassId, serialNum = objRefSplit(objRef)
			if klassId == 0 or serialNum == 0:
				# invalid! we don't use 0 serial numbers
				return self.objRefZeroSerialNum(objRef)

			klass = self.klassForId(klassId)

			# Check if we already have this in memory first
			key = ObjectKey()
			key.initFromClassNameAndSerialNum(klass.name(), serialNum)
			obj = self._objects.get(key, None)
			if obj:
				return obj

			clauses = 'where %s=%d' % (klass.sqlSerialColumnName(), serialNum)
			objs = self.fetchObjectsOfClass(klass, clauses, isDeep=False)
			if len(objs) == 1:
				return objs[0]
			elif len(objs) > 1:
				raise ValueError, 'Multiple objects.' # @@ 2000-11-22 ce: expand the msg with more information
			else:
				return self.objRefDangles(objRef)

	def objRefInMem(self, objRef):
		""" Return the object corresponding to the given objref if and only
		if it has been loaded into memory.  If the object has never been
		fetched from the database, None is returned. """
		assert isinstance(objRef, types.LongType), 'type=%r, objRef=%r' % (type(objRef), objRef)
		if objRef == 0:
			return 0
		else:
			klassId, serialNum = objRefSplit(objRef)
			if klassId == 0 or serialNum == 0:
				# invalid! we don't use 0 serial numbers
				return self.objRefZeroSerialNum(objRef)

			klass = self.klassForId(klassId)

			# return whether we have this object in memory
			key = ObjectKey()
			key.initFromClassNameAndSerialNum(klass.name(), serialNum)
			return self._objects.get(key, None)

	def objRefZeroSerialNum(self, objRef):
		""" Invoked by fetchObjRef() if either the class or object serial number is 0. """
		raise ObjRefZeroSerialNumError, objRefSplit(objRef)

	def objRefDangles(self, objRef):
		""" Invoked by fetchObjRef() if there is no possible target object for the given objRef, e.g., a dangling reference. This method invokes self.warning() and includes the objRef as decimal, hexadecimal and class:obj numbers. """
		raise ObjRefDanglesError, objRefSplit(objRef)


	## Special Cases ##

	def filterDateTimeDelta(self, dtd):
		"""
		Some databases have no TIME type and therefore will not return DateTimeDeltas.
		This utility method is overridden by subclasses as appropriate and invoked by
		the test suite.
		"""
		return dtd

	def sqlNowCall(self):
		return 'Now()'


	## Self util ##

	def doneWithConnection(self, conn):
		"""
		Invoked by self when a connection is no longer needed.
		The default behavior is to close the connection.
		"""
		if conn is not None:
			# Starting with 1.2.0, MySQLdb disables autocommit by default,
			# as required by the DB-API standard (PEP-249). If you are using
			# InnoDB tables or some other type of transactional table type,
			# you'll need to do connection.commit() before closing the connection,
			# or else none of your changes will be written to the database.
			try:
				conn.commit()
			except:
				pass
			conn.close()


	## Debugging ##

	def dumpTables(self, out=None):
		if out is None:
			out = sys.stdout
		out.write('DUMPING TABLES\n')
		out.write('BEGIN\n')
		conn = None
		try:
			for klass in self.model().klasses().values():
				out.write(klass.name() + '\n')
				conn, cur = self.executeSQL('select * from %s;' % klass.name(), conn)
				out.write(str(self._cursor.fetchall()))
				out.write('\n')
		finally:
			self.doneWithConnection(conn)
		out.write('END\n')

	def dumpKlassIds(self, out=None):
		if out is None:
			out = sys.stdout
		wr = out.write('DUMPING KLASS IDs\n')
		for klass in self.model().klasses().values():
			out.write('%25s %2i\n' % (klass.name(), klass.id()))
		out.write('\n')

	def dumpObjectStore(self, out=None, progress=False):
		if out is None:
			out = sys.stdout
		for klass in self.model().klasses().values():
			if progress:
				sys.stderr.write(".")
			out.write('%s objects\n' % (klass.name()))
			attrs = [attr for attr in klass.allAttrs() if attr.hasSQLColumn()]
			colNames = [attr.name() for attr in attrs]
			colNames.insert(0, klass.sqlSerialColumnName())
			out.write(CSVJoiner.joinCSVFields(colNames) + "\n")

			# write out a line for each object in this class
			objlist = self.fetchObjectsOfClass(klass.name(), isDeep=False)
			for obj in objlist:
				fields = []
				fields.append(str(obj.serialNum()))
				for attr in attrs:
					# jdh 2003-03-07: if the attribute is a dangling object reference, the value
					# will be None.  This means that dangling references will _not_ be remembered
					# across dump/generate/create/insert procedures.
					method = getattr(obj, attr.pyGetName())
					value = method()
					if value is None:
						fields.append('')
					elif isinstance(value, MiddleObject):
						fields.append(value.klass().name() + "." + str(value.serialNum()))
					else:
						fields.append(str(value))
				out.write(CSVJoiner.joinCSVFields(fields).replace('\r', '\\r'))

				out.write('\n')
			out.write('\n')
		out.write('\n')
		if progress:
			sys.stderr.write("\n")


class Model:

	def sqlDatabaseName(self):
		"""
		Returns the name of the database (which is either the 'Database'
		setting or self.name()).
		"""
		name = self.setting('Database', None)
		if name is None:
			name = self.name()
		return name


class MiddleObjectMixIn:

	def sqlObjRef(self):
		"""
		Returns the 64-bit integer value that refers to self in a SQL database.
		This only makes sense if the UseBigIntObjRefColumns setting is True.
		"""
		return objRefJoin(self.klass().id(), self.serialNum())

	def sqlInsertStmt(self, unknowns, id=None):
		"""
		Returns the SQL insert statements for MySQL (as a tuple) in the form:
			insert into table (name, ...) values (value, ...);

		May add an info object to the unknowns list for obj references that
		are not yet resolved.
		"""
		klass = self.klass()
		insertSQLStart, sqlAttrs = klass.insertSQLStart(includeSerialColumn=id)
		values = []
		append = values.append
		extend = values.extend
		if id is not None:
			append(str(id))
		for attr in sqlAttrs:
			try:
				value = attr.sqlValue(self.valueForAttr(attr))
			except UnknownSerialNumberError, exc:
				exc.info.sourceObject = self
				unknowns.append(exc.info)
				if self.store().model().setting('UseBigIntObjRefColumns', False):
					value = 'NULL'
				else:
					value = ('NULL', 'NULL')
			if type(value) in StringTypes:
				append(value)
			else:
				extend(value)  # value could be sequence for attrs that require multiple SQL columns
		if len(values) == 0:
			values = ['0']
		values = ','.join(values)
		return insertSQLStart + values + ');'

	def sqlUpdateStmt(self):
		"""
		Returns the SQL update statement of the form:
			update table set name=value, ... where idName=idValue;
		Installed as a method of MiddleObject.
		"""
		assert self._mk_changedAttrs
		klass = self.klass()
		res = []
		for attr in self._mk_changedAttrs.values():
			res.append(attr.sqlUpdateExpr(self.valueForAttr(attr)))
		res = ','.join(res)
		res = ('update ', klass.sqlTableName(), ' set ', res, ' where ', klass.sqlSerialColumnName(), '=', str(self.serialNum()))
		return ''.join(res)

	def sqlDeleteStmt(self):
		"""
		Returns the SQL delete statement for MySQL of the form:
			delete from table where idName=idValue;
		Or if deletion is being marked with a timestamp:
			update table set deleted=Now();
		Installed as a method of MiddleObject.
		"""
		klass = self.klass()
		assert klass is not None
		if self.store().model().setting('DeleteBehavior', 'delete') == 'mark':
			return 'update %s set deleted=%s where %s=%d;' % (klass.sqlTableName(), self.store().sqlNowCall(), klass.sqlSerialColumnName(), self.serialNum())
		else:
			return 'delete from %s where %s=%d;' % (klass.sqlTableName(), klass.sqlSerialColumnName(), self.serialNum())

	def referencingObjectsAndAttrsFetchKeywordArgs(self, backObjRefAttr):
		if self.store().setting('UseBigIntObjRefColumns'):
			return {
				'refreshAttrs': True,
				'clauses': 'WHERE %s=%s' % (backObjRefAttr.sqlColumnName(), self.sqlObjRef())
			}
		else:
			classIdName, objIdName = backObjRefAttr.sqlColumnNames()
			return {
				'refreshAttrs': True,
				'clauses': 'WHERE (%s=%s AND %s=%s)' % (classIdName, self.klass().id(), objIdName, self.serialNum())
			}

MixIn(MiddleObject, MiddleObjectMixIn)
	# Normally we don't have to invoke MixIn()--it's done automatically.
	# However, that only works when augmenting MiddleKit.Core classes
	# (MiddleObject belongs to MiddleKit.Run).


import MiddleKit.Design.KlassSQLSerialColumnName


class Klass:

	_fetchSQLStart = None  # help out the caching mechanism in fetchSQLStart()
	_insertSQLStart = None  # help out the caching mechanism in insertSQLStart()

	def sqlTableName(self):
		"""
		Returns the name of the SQL table for this class.
		Returns self.name().
		Subclasses may wish to override to provide special quoting that
		prevents name collisions between table names and reserved words.
		"""
		return self.name()

	def fetchSQLStart(self):
		if self._fetchSQLStart is None:
			attrs = self.allDataAttrs()
			attrs = [attr for attr in attrs if attr.hasSQLColumn()]
			colNames = [self.sqlSerialColumnName()]
			colNames.extend([attr.sqlColumnName() for attr in attrs])
			self._fetchSQLStart = 'select %s from %s ' % (','.join(colNames), self.sqlTableName())
		return self._fetchSQLStart

	def insertSQLStart(self, includeSerialColumn=False):
		"""
		Returns a tuple of insertSQLStart (a string) and sqlAttrs (a list).
		"""
		if self._insertSQLStart is None:
			res = ['insert into %s (' % self.sqlTableName()]
			attrs = self.allDataAttrs()
			attrs = [attr for attr in attrs if attr.hasSQLColumn()]
			fieldNames = [attr.sqlColumnName() for attr in attrs]
			if includeSerialColumn or len(fieldNames) == 0:
				fieldNames.insert(0, self.sqlSerialColumnName())
			res.append(','.join(fieldNames))
			res.append(') values (')
			self._insertSQLStart = ''.join(res)
			self._sqlAttrs = attrs
		return self._insertSQLStart, self._sqlAttrs


class Attr:

	def shouldRegisterChanges(self):
		""" Returns self.hasSQLColumn(). This only makes sense since there would be no point in registering changes on an attribute with no corresponding SQL column. The standard example of such an attribute is "list". """
		return self.hasSQLColumn()

	def hasSQLColumn(self):
		""" Returns true if the attribute has a direct correlating SQL column in it's class' SQL table definition. Most attributes do. Those of type list do not. """
		return not self.get('isDerived', False)

	def sqlColumnName(self):
		""" Returns the SQL column name corresponding to this attribute, consisting of self.name() + self.sqlTypeSuffix(). """
		if not self._sqlColumnName:
			self._sqlColumnName = self.name()
		return self._sqlColumnName

	def sqlValue(self, value):
		"""
		For a given Python value, this returns the correct string for
		use in a SQL statement. Subclasses will typically *not*
		override this method, but instead, sqlForNonNone() and on
		rare occasions, sqlForNone().
		"""
		if value is None:
			return self.sqlForNone()
		else:
			return self.sqlForNonNone(value)

	def sqlForNone(self):
		return 'NULL'

	def sqlForNonNone(self, value):
		return repr(value)

	def sqlUpdateExpr(self, value):
		"""
		Returns the assignment portion of an UPDATE statement such as:
			"foo='bar'"
		Using sqlColumnName() and sqlValue(). Subclasses only need to
		override this if they have a special need (such as multiple
		columns, see ObjRefAttr).
		"""
		colName = self.sqlColumnName()
		return colName + '=' + self.sqlValue(value)

	def readStoreDataRow(self, obj, row, i):
		"""
		By default, an attr reads one data value out of the row.
		"""
		value = row[i]
		obj.setValueForAttr(self, value)
		return i + 1


class BasicTypeAttr:

	pass


class IntAttr:

	def sqlForNonNone(self, value):
		return str(value)
		# it's important to use str() since an int might
		# point to a long (whose repr() would be suffixed
		# with an 'L')


class LongAttr:

	def sqlForNonNone(self, value):
		return str(value)


class DecimalAttr:

	def sqlForNonNone(self, value):
		return str(value) # repr() can give Decimal("3.4") in Python 2.4


class BoolAttr:

	def sqlForNonNone(self, value):
		return value and '1' or '0' # MySQL and MS SQL will take 1 and 0 for bools


class ObjRefAttr:

	def sqlColumnName(self):
		if not self._sqlColumnName:
			if self.setting('UseBigIntObjRefColumns', False):
				self._sqlColumnName = self.name() + 'Id'  # old way: one 64 bit column
			else:
				# new way: 2 int columns for class id and obj id
				self._sqlColumnName = '%s,%s' % self.sqlColumnNames()
		return self._sqlColumnName

	def sqlColumnNames(self):
		if not self._sqlColumnNames:
			assert not self.setting('UseBigIntObjRefColumns', False)
			name = self.name()
			classIdName, objIdName = self.setting('ObjRefSuffixes')
			classIdName = name + classIdName
			objIdName = name + objIdName
			self._sqlColumnNames = (classIdName, objIdName)
		return self._sqlColumnNames

	def sqlForNone(self):
		if self.setting('UseBigIntObjRefColumns', False):
			return 'NULL'
		else:
			return 'NULL,NULL'

	def sqlForNonNone(self, value):
		assert isinstance(value, MiddleObject)
		if value.serialNum() == 0:
			info = UnknownSerialNumInfo()
			info.sourceAttr = self
			info.targetObject = value
			raise UnknownSerialNumberError(info)
		else:
			if self.setting('UseBigIntObjRefColumns', False):
				return str(value.sqlObjRef())
			else:
				return (str(value.klass().id()), str(value.serialNum()))

	def sqlUpdateExpr(self, value):
		"""
		Returns the assignment portion of an UPDATE statement such as:
			"foo='bar'"
		Using sqlColumnName() and sqlValue(). Subclasses only need to
		override this if they have a special need (such as multiple
		columns, see ObjRefAttr).
		"""
		if self.setting('UseBigIntObjRefColumns', False):
			colName = self.sqlColumnName()
			return colName + '=' + self.sqlValue(value)
		else:
			classIdName, objIdName = self.sqlColumnNames()
			if value is None:
				classId = objId = 'NULL'
			else:
				classId = value.klass().id()
				objId = value.serialNum()
			return '%s=%s,%s=%s' % (classIdName, classId, objIdName, objId)

	def readStoreDataRow(self, obj, row, i):
		# this does *not* get called under the old approach of single obj ref columns. see MiddleObject.readStoreData
		classId, objId = row[i], row[i+1]
		if objId is None:
			value = None
		else:
			value = objRefJoin(classId, objId)
			# @@ 2004-20-02 ce ^ that's wasteful to join them just so they can be split later, but it works well with the legacy code
		obj.setValueForAttr(self, value)
		return i + 2


class ListAttr:

	def hasSQLColumn(self):
		return False

	def readStoreDataRow(self, obj, row, i):
		return i


class AnyDateTimeAttr:

	def sqlForNonNone(self, value):
		# Chop off the milliseconds -- SQL databases seem to dislike that.
		return "'%s'" % str(value).split('.')[0]


class DateAttr:

	def sqlForNonNone(self, value):
		# We often get "YYYY-MM-DD HH:MM:SS" from mx's DateTime
		# so we split on space and take the first value to
		# work around that. This works fine with Python's
		# date class (does no harm).
		if 0:
			print
			print '>> type of value =', type(value)
			print '>> value = %r' % value
			print
		if not type(value) in StringTypes:
			value = str(value).split()[0]
		return "'%s'" % value
