from SQLObjectStore import SQLObjectStore
from mx import ODBC # DR: 07-12-02 The ODBC.Windows module is flawed
ODBC.Windows.threadsafety = ODBC.Windows.threadlevel
# mx.ODBC.Windows has a threadlevel, not a threadsafety,
# even though DBABI2.0 says its threadsafety
# (http://www.python.org/topics/database/DatabaseAPI-2.0.html)

try: # for Python < 2.3
	True, False
except NameError:
	True, False = 1, 0


class MSSQLObjectStore(SQLObjectStore):
	_threadSafety = ODBC.Windows.threadsafety
	"""
	MSSQLObjectStore does the obvious: it implements an object store backed by a MSSQL database.

	mx.ODBC is required, which in turn requires mx BASE:
	http://egenix.com/files/python/

	Example creation:
		from MiddleKit.Run.MSSQLObjectStore import MSSQLObjectStore
		store = MSSQLObjectStore(dsn='LocalServer', clear_auto_commit=0)

	As usual, the keyword args are passed through to the DB API connect()
	function.

	Interesting notes from mx.ODBC docs:
	- - -
	If you have troubles with multiple cursors on connections to MS SQL
	Server the MS Knowledge Base Article INF: Multiple Active Microsoft
	SQL Server Statements has some valuable information for you. It
	seems that you'll have to force the usage of server side cursors
	to be able to execute multiple statements on a single connection to
	MS SQL Server. According to the article this is done by setting the
	connection option SQL.CURSOR_TYPE to e.g. SQL.CURSOR_DYNAMIC:

		dbc.setconnectoption(SQL.CURSOR_TYPE, SQL.CURSOR_DYNAMIC)
	- - -
	"""

	def dbapiConnect(self):
		"""
		Returns a DB API 2.0 connection. This is a utility method invoked by connect(). Subclasses should implement this, making use of self._dbArgs (a dictionary specifying host, username, etc.).
		Subclass responsibility.
		MSSQL 2000 defaults to autocommit ON (at least mine does)
		if you want it off, do not send any arg for clear_auto_commit or set it to 1
		# self._db = ODBC.Windows.Connect(dsn='myDSN',clear_auto_commit=0)
		"""
		return ODBC.Windows.Connect(**self._dbArgs)

	def retrieveLastInsertId(self, conn, cur):
		conn, cur = self.executeSQL('select @@IDENTITY', conn)
		value = int(cur.fetchone()[0])
		self.doneWithConnection(conn)
		return value

	def newConnection(self):
		args = self._dbArgs.copy()
		if args.get('DriverConnect'):
			# @@ problem here is that clear_auto_commit can't be set to zero
			# example: storeArgs = {'DriverConnect': 'DRIVER=SQL Server;UID=echuck;Trusted_Connection=Yes;WSID=ALIEN;SERVER=ALIEN'}
			# ODBC driver connection keywords are documented here:
			# http://msdn.microsoft.com/library/default.asp?url=/library/en-us/odbcsql/od_odbc_d_4x4k.asp
			s = args['DriverConnect']
			if s.find('DATABASE=') == -1:
				if s[-1] != ';':
					s += ';'
				s += 'DATABASE=' + self._model.sqlDatabaseName()
			# print '>> connection string=%r' % s
			conn = self.dbapiModule().DriverConnect(s)
		else:
			# extract the database arg if it was provided
			if args.has_key('database'):
				database = args['database']
				del args['database']
			else:
				database = None
			conn = self.dbapiModule().connect(**args)
			cur = conn.cursor()
			try:
				db = database or self._model.sqlDatabaseName()
				sql = 'use ' + db + ';'
				# print '>> use string=%r' % sql
				cur.execute(sql)
			except Exception, e:
				if e.args[0] != '01000':
					# ('01000', 5701, "[Microsoft][ODBC SQL Server Driver]"
					# "[SQL Server]Changed database context to 'MKList'.", 4612)
					raise
		return conn

	def dbapiModule(self):
		return ODBC.Windows

	def filterDateTimeDelta(self, dtd):
		from mx import DateTime
		if isinstance(dtd, DateTime.DateTimeDeltaType):
			dtd = DateTime.DateTime(1900, 1, 1) + dtd
		return dtd

	def sqlNowCall(self):
		return 'GETDATE()'


class Klass:

	def sqlTableName(self):
		"""
		Returns "[name]" so that table names do not conflict with SQL
		reserved words.
		"""
		return '[%s]' % self.name()


class Attr:

	def sqlColumnName(self):
		if not self._sqlColumnName:
			self._sqlColumnName = '[' + self.name() + ']'
		return self._sqlColumnName


class ObjRefAttr:

	def sqlColumnName(self):
		if not self._sqlColumnName:
			if self.setting('UseBigIntObjRefColumns', False):
				self._sqlColumnName = '[' + self.name() + 'Id' + ']'  # old way: one 64 bit column
			else:
				# new way: 2 int columns for class id and obj id
				self._sqlColumnName = '[%s],[%s]' % self.sqlColumnNames()
		return self._sqlColumnName


class StringAttr:

	def sqlForNonNone(self, value):
		# do the right thing
		value = value.replace("'", "''")
		return "'" + value + "'"
