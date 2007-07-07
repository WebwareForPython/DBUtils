import sys
from SQLObjectStore import SQLObjectStore
from MiddleKit.Run.ObjectKey import ObjectKey
from MiddleObject import MiddleObject
from MiscUtils.MixIn import MixIn
import psycopg as dbi  # psycopg adapter; apt-get install python2.2-psycopg
from psycopg import Warning, DatabaseError
from SQLObjectStore import UnknownSerialNumberError
from MiscUtils import NoDefault


class PostgreSQLObjectStore(SQLObjectStore):
	"""
	PostgresObjectStore does the obvious: it implements an object store backed by a PostgreSQL database.

	The connection arguments passed to __init__ are:
		- host
		- user
		- passwd
		- port
		- unix_socket
		- client_flag

	You wouldn't use the 'db' argument, since that is determined by the model.
	"""

	def setting(self, name, default=NoDefault):
		# jdh: psycopg doesn't seem to work well with DBPool -- I've experienced
		# requests blocking indefinitely (deadlock?).  Besides, it does its
		# own connection pooling internally, so DBPool is unnecessary.
		if name == 'SQLConnectionPoolSize':
			return 0
		return SQLObjectStore.setting(self, name, default)

	def newConnection(self):
		args = self._dbArgs.copy()
		self.augmentDatabaseArgs(args)
		return self.dbapiModule().connect(**args)

	def doneWithConnection(self, conn):
		# psycopg doesn't like connections to be closed presumably because of pooling
		pass

	def augmentDatabaseArgs(self, args, pool=0):
		if not args.get('database'):
			args['database'] = self._model.sqlDatabaseName()

	def newCursorForConnection(self, conn, dictMode=0):
		return conn.cursor()

	def retrieveNextInsertId(self, klass):
		seqname = "%s_%s_seq" % (klass.name(), klass.sqlSerialColumnName())
		conn, curs = self.executeSQL("select nextval('%s')" % seqname)
		id = curs.fetchone()[0]
		assert id, "Didn't get next id value from sequence"
		return id

	def dbapiModule(self):
		return dbi

	def _executeSQL(self, cur, sql):
		try:
			cur.execute(sql)
		except Warning, e:
			if not self.setting('IgnoreSQLWarnings', 0):
				raise

	def saveChanges(self):
		conn, cur = self.connectionAndCursor()
		try:

			SQLObjectStore.saveChanges(self)
		except DatabaseError:
			conn.rollback()
			raise
		except Warning:
			if not self.setting('IgnoreSQLWarnings', 0):
				conn.rollback()
				raise
		conn.commit()

	def sqlCaseInsensitiveLike(self, a, b):
		return "%s ilike %s" % (a, b)


class StringAttr:

	def sqlForNonNone(self, value):
		"""psycopg provides a quoting function for string -- use it."""
		return "%s" % dbi.QuotedString(value)


class BoolAttr:

	def sqlForNonNone(self, value):
		if value:
			return 'TRUE'
		else:
			return 'FALSE'
