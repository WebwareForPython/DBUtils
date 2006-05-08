"""SolidDB - hardened DB-API 2 connections.

Implements solid connections to a database based on an
arbitrary DB-API 2 compliant database interface module.

The connections are transparently reopened when they are
closed or the database connection has been lost or when
they are used more often than an optional usage limit.
Database cursors are transparently reopened as well when
the execution of a database operation cannot be performed
due to a lost connection. Only if the connection is lost
after the execution, when rows are already fetched from the
database, this will give an error and the cursor will not
be reopened automatically, because there is no reliable way
to recover the state of the cursor in such a situation.

A typical situation where database connections are lost
is when the database server or an intervening firewall is
shutdown and restarted for maintenance reasons. In such a
case, all database connections would become unusuable, even
though the database service may be already available again.

The "hardened" connections provided by this module will
make the database connections immediately available again.

This approach results in a solid database connection that
can be used by PooledDB or PersistentDB to create pooled or
persistent connections to a database in a threaded environment
such as the application server of "Webware for Python."
Note, however, that the connections themselves may not be
thread-safe (depending on the used DB-API module).

For the Python DB-API 2 specification, see:
	http://www.python.org/peps/pep-0249.html
For information on Webware for Python, see:
	http://www.webwareforpython.org

Usage:

You can use the connection construtctor connect() in the same
way as you would use the same constructor of the DB-API 2 module.
The only difference is that you have to specify the DB-API 2
module to be used as a first parameter, and you may also specify
a usage limit as the second paramenter (set it to 0 if you prefer
unlimited usage), and an optional list of commands that may serve
to prepare the session as a third parameter. When the connection
to the database is lost or has been used too often, it will be
transparently reset in most situations, without further notice.

	import pgdb # import used DB-API 2 module
	from SolidDB import connect
	db = connect(pgdb, 10000, ["set datestyle to german"],
		host=..., database=..., user=..., ...)
	...
	cursor = db.cursor()
	...
	cursor.execute('select ...')
	result = cursor.fetchall()
	...
	cursor.close()
	...
	db.close()


Ideas for improvement:

* Alternatively to the maximum number of uses,
  implement a maximum time to live for connections.
* Optionally log usage and loss of connection.


Copyright, credits and license:

* Contributed as supplement for Webware for Python and PyGreSQL
  by Christoph Zwerschke in September 2005

Licensed under the Open Software License version 2.1.

"""

__version__ = '0.9.1'
__revision__ = "$Rev$"
__date__ = "$Date$"


def connect(dbapi, maxusage=0, setsession=None, *args, **kwargs):
	"""A tough version of the connection constructor of a DB-API 2 module.

	dbapi: the DB-API 2 compliant database module to be used
	maxusage: maximum usage limit for the underlying DB-API 2 connection
		(number of database operations, 0 or False means unlimited usage)
		callproc(), execute() and executemany() count as one operation
		When the limit is reached, the connection is automatically reset.
	setsession: an optional list of SQL commands that may serve to prepare
		the session, e.g. ["set datestyle to german", "set time zone mez"]
	args, kwargs: the parameters that shall be used to establish the
		connection with the connection constructor of the DB-API 2 module

	"""
	return SolidDBConnection(dbapi, maxusage, setsession, *args, **kwargs)


class SolidDBConnection:
	"""A "tough" version of DB-API 2 connections."""

	def __init__(self, dbapi, maxusage=0, setsession=None, *args, **kwargs):
		""""Create a "tough" DB-API 2 connection."""
		self._dbapi = dbapi
		self._maxusage = maxusage
		self._setsession_sql = setsession
		self._args, self._kwargs = args, kwargs
		self._closeable = 1
		self._usage = 0
		self._con = dbapi.connect(*args, **kwargs)
		self._setsession()

	def _setsession(self, con=None):
		"""Execute the SQL commands for session preparation."""
		if con is None:
			con = self._con
		if self._setsession_sql:
			cursor = con.cursor()
			for sql in self._setsession_sql:
				cursor.execute(sql)
			cursor.close()

	def _close(self):
		"""Close the tough connection.

		You can always close a tough connection with this method
		and it will not complain if you close it more than once.

		"""
		try:
			self._con.close()
		except:
			pass
		self._usage = 0

	def close(self):
		"""Close the tough connection.

		You are allowed to close a tough connection by default
		and it will not complain if you close it more than once.

		You can disallow closing connections by setting
		the _closeable attribute to 0 or False. In this case,
		closing a connection will be silently ignored.

		"""
		if self._closeable:
			self._close()

	def commit(self):
		"""Commit any pending transaction."""
		self._con.commit()

	def rollback(self):
		"""Rollback pending transaction."""
		self._con.rollback()

	def _cursor(self, *args, **kwargs):
		"""A "tough" version of the method cursor()."""
		# The args and kwargs are not part of the standard,
		# but some database modules seem to use these.
		try:
			if self._maxusage:
				if self._usage >= self._maxusage:
					# the connection was used too often
					raise self._dbapi.OperationalError
			r = self._con.cursor(*args, **kwargs) # try to get a cursor
		except (self._dbapi.OperationalError,
			self._dbapi.InternalError): # error in getting cursor
			try: # try to reopen the connection
				con2 = self._dbapi.connect(*self._args, **self._kwargs)
				self._setsession(con2)
			except:
				pass
			else:
				try: # and try one more time to get a cursor
					r = con2.cursor(*args, **kwargs)
				except:
					pass
				else:
					self._close()
					self._con = con2
					return r
				try:
					con2._close()
				except:
					pass
			raise # raise the original error again
		return r

	def cursor(self, *args, **kwargs):
		"""Return a new Cursor Object using the connection."""
		return SolidDBCursor(self, *args, **kwargs)


class SolidDBCursor:
	"""A "tough" version of DB-API 2 cursors."""

	def __init__(self, con, *args, **kwargs):
		""""Create a "tough" DB-API 2 cursor."""
		self._con = con
		self._args, self._kwargs = args, kwargs
		self._clearsizes()
		self._cursor = con._cursor(*args, **kwargs)

	def setinputsizes(self, sizes):
		"""Store input sizes in case cursor needs to be reopened."""
		self._inputsize = sizes

	def setoutputsize(self, size, column=None):
		"""Store output sizes in case cursor needs to be reopened."""
		if self._outputsize is None or column is None:
			self._outputsize = [(column, size)]
		else:
			self._outputsize.append(column, size)

	def _clearsizes(self):
		"""Clear stored input sizes."""
		self._inputsize = self._outputsize = None

	def _setsizes(self, cursor=None):
		"""Set stored input and output sizes for cursor execution."""
		if cursor is None:
			cursor = self._cursor
		if self._inputsize is not None:
			cursor.setinputsizes(self._inputsize)
		if self._outputsize is not None:
			for column, size in self._outputsize:
				if column is None:
					cursor.setoutputsize(size)
				else:
					cursor.setoutputsize(size, column)

	def close(self):
		"""Close the tough cursor.

		It will not complain if you close it more than once.

		"""
		try:
			self._cursor.close()
		except:
			pass

	def _get_tough_method(self, name):
		"""Return a "tough" version of the method."""
		def tough_method(*args, **kwargs):
			execute = name.startswith('execute')
			try:
				if self._con._maxusage:
					if self._con._usage >= self._con._maxusage:
						# the connection was used too often
						raise self._con._dbapi.OperationalError
				if execute:
					self._setsizes()
				method = getattr(self._cursor, name)
				r = method(*args, **kwargs) # try to execute
				if execute:
					self._clearsizes()
			except (self._con._dbapi.OperationalError,
				self._con._dbapi.InternalError): # execution error
				try:
					cursor2 = self._con._cursor(
						*self._args, **self._kwargs) # open new cursor
				except:
					pass
				else:
					try: # and try one more time to execute
						if execute:
							self._setsizes(cursor2)
						method = getattr(cursor2, name)
						r = method(*args, **kwargs)
						if execute:
							self._clearsizes()
					except:
						pass
					else:
						self.close()
						self._cursor = cursor2
						self._con._usage += 1
						return r
					try:
						cursor2.close()
					except:
						pass
				try: # try to reopen the connection
					con2 = self._con._dbapi.connect(
						*self._con._args, **self._con._kwargs)
					self._con._setsession(con2)
				except:
					pass
				else:
					try:
						cursor2 = con2.cursor(
							*self._args, **self._kwargs) # open new cursor
					except:
						pass
					else:
						try: # try one more time to execute
							if execute:
								self._setsizes(cursor2)
							method2 = getattr(cursor2, name)
							r = method2(*args, **kwargs)
							if execute:
								self._clearsizes()
						except:
							pass
						else:
							self.close()
							self._con._close()
							self._con._con, self._cursor = con2, cursor2
							self._con._usage += 1
							return r
						try:
							cursor2.close()
						except:
							pass
					try:
						con2._close()
					except:
						pass
				raise # raise the original error again
			else:
				self._con._usage += 1
				return r
		return tough_method

	def __getattr__(self, name):
		"""Inherit methods and attributes of underlying cursor."""
		if name.startswith('execute') or name.startswith('call'):
			# make execution methods "tough"
			return self._get_tough_method(name)
		else:
			return getattr(self._cursor, name)
