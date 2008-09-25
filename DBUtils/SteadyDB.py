"""SteadyDB - hardened DB-API 2 connections.

Implements steady connections to a database based on an
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
case, all database connections would become unusable, even
though the database service may be already available again.

The "hardened" connections provided by this module will
make the database connections immediately available again.

This approach results in a steady database connection that
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

You can use the connection constructor connect() in the same
way as you would use the connection constructor of a DB-API 2
module if you specify the DB-API 2 module to be used as the
first parameter, or alternatively you can specify an arbitrary
constructor function returning new DB-API 2 compliant connection
objects as the first parameter. Passing just a function allows
implementing failover mechanisms and load balancing strategies.

You may also specify a usage limit as the second parameter
(set it to 0 if you prefer unlimited usage), and an optional
list of commands that may serve to prepare the session as a
third parameter. When the connection to the database is lost
or has been used too often, it will be transparently reset
in most situations, without further notice.

	import pgdb # import used DB-API 2 module
	from DBUtils.SteadyDB import connect
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
* Allowing creator functions as first parameter as in SQLAlchemy
  suggested by Ezio Vernacotola in December 2006

Licensed under the Open Software License version 2.1.

"""

__version__ = '1.0pre'
__revision__ = "$Rev$"
__date__ = "$Date$"


import sys


def connect(creator, maxusage=None, setsession=None, failures=None,
		closeable=True, *args, **kwargs):
	"""A tough version of the connection constructor of a DB-API 2 module.

	creator: either an arbitrary function returning new DB-API 2 compliant
		connection objects or a DB-API 2 compliant database module
	maxusage: maximum usage limit for the underlying DB-API 2 connection
		(number of database operations, 0 or None means unlimited usage)
		callproc(), execute() and executemany() count as one operation.
		When the limit is reached, the connection is automatically reset.
	setsession: an optional list of SQL commands that may serve to prepare
		the session, e.g. ["set datestyle to german", "set time zone mez"]
	failures: an optional exception class or a tuple of exception classes
		for which the failover mechanism shall be applied, if the default
		(OperationalError, InternalError) is not adequate
	closeable: if this is set to false, then closing the connection will
		be silently ignored, but by default the connection can be closed
	args, kwargs: the parameters that shall be passed to the creator
		function or the connection constructor of the DB-API 2 module

	"""
	return SteadyDBConnection(creator, maxusage, setsession, failures,
		closeable, *args, **kwargs)


class SteadyDBConnection:
	"""A "tough" version of DB-API 2 connections."""

	version = __version__

	_closed = True

	def __init__(self, creator, maxusage=None, setsession=None, failures=None,
			closeable=True, *args, **kwargs):
		""""Create a "tough" DB-API 2 connection."""
		try:
			self._creator = creator.connect
			self._dbapi = creator
		except AttributeError:
			self._creator = creator
			try:
				self._dbapi = sys.modules[creator.__module__]
				if self._dbapi.connect != creator:
					raise AttributeError
			except (AttributeError, KeyError):
				self._dbapi = None
		if not callable(self._creator):
			raise TypeError("%r is not a connection provider." % (creator,))
		if maxusage is not None and not isinstance(maxusage, (int, long)):
			raise TypeError("'maxusage' must be an integer value.")
		self._maxusage = maxusage
		self._setsession_sql = setsession
		if failures is not None and not isinstance(
				failures, tuple) and not issubclass(failures, Exception):
			raise TypeError("'failures' must be a tuple of exceptions.")
		self._failures = failures
		self._closeable = closeable
		self._args, self._kwargs = args, kwargs
		self._store(self._create())

	def _create(self):
		"""Create a new connection using the creator function."""
		con = self._creator(*self._args, **self._kwargs)
		try:
			try:
				if self._dbapi.connect != self._creator:
					raise AttributeError
			except AttributeError:
				try:
					self._dbapi = sys.modules[con.__module__]
					if not callable(self._dbapi.connect):
						raise AttributeError
				except (AttributeError, KeyError):
					raise TypeError("Cannot determine DB-API 2 module.")
			if self._failures is None:
				self._failures = (self._dbapi.OperationalError,
					self._dbapi.InternalError)
			self._setsession(con)
		except Exception, error:
			# the database module could not be determined
			# or the session could not be prepared
			try: # close the connection first
				con.close()
			except Exception:
				pass
			raise error # reraise the original error again
		return con

	def _setsession(self, con=None):
		"""Execute the SQL commands for session preparation."""
		if con is None:
			con = self._con
		if self._setsession_sql:
			cursor = con.cursor()
			for sql in self._setsession_sql:
				cursor.execute(sql)
			cursor.close()

	def _store(self, con):
		"""Store a database connection for subsequent use."""
		self._con = con
		self._closed = False
		self._usage = 0

	def _close(self):
		"""Close the tough connection.

		You can always close a tough connection with this method
		and it will not complain if you close it more than once.

		"""
		if not self._closed:
			try:
				self._con.close()
			except Exception:
				pass
			self._closed = True

	def dbapi(self):
		"""Return the underlying DB-API 2 module of the connection."""
		return self._dbapi

	def threadsafety(self):
		"""Return the thread safety level of the connection."""
		try:
			return self._dbapi.threadsafety
		except AttributeError:
			return 0

	def close(self):
		"""Close the tough connection.

		You are allowed to close a tough connection by default
		and it will not complain if you close it more than once.

		You can disallow closing connections by setting
		the closeable parameter to something false. In this case,
		closing tough connections will be silently ignored.

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
			cursor = self._con.cursor(*args, **kwargs) # try to get a cursor
		except self._failures, error: # error in getting cursor
			try: # try to reopen the connection
				con2 = self._create()
			except Exception:
				pass
			else:
				try: # and try one more time to get a cursor
					cursor = con2.cursor(*args, **kwargs)
				except Exception:
					pass
				else:
					self._close()
					self._store(con2)
					return cursor
				try:
					con2.close()
				except Exception:
					pass
			raise error # reraise the original error again
		return cursor

	def cursor(self, *args, **kwargs):
		"""Return a new Cursor Object using the connection."""
		return SteadyDBCursor(self, *args, **kwargs)

	def __del__(self):
		"""Delete the steady connection."""
		try:
			self._close() # make sure the connection is closed
		except Exception:
			pass


class SteadyDBCursor:
	"""A "tough" version of DB-API 2 cursors."""

	_closed = True

	def __init__(self, con, *args, **kwargs):
		""""Create a "tough" DB-API 2 cursor."""
		self._con = con
		self._args, self._kwargs = args, kwargs
		self._clearsizes()
		self._cursor = con._cursor(*args, **kwargs)
		self._closed = False

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
		if not self._closed:
			try:
				self._cursor.close()
			except Exception:
				pass
			self._closed = True

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
				result = method(*args, **kwargs) # try to execute
				if execute:
					self._clearsizes()
			except self._con._failures, error: # execution error
				try:
					cursor2 = self._con._cursor(
						*self._args, **self._kwargs) # open new cursor
				except Exception:
					pass
				else:
					try: # and try one more time to execute
						if execute:
							self._setsizes(cursor2)
						method = getattr(cursor2, name)
						result = method(*args, **kwargs)
						if execute:
							self._clearsizes()
					except Exception:
						pass
					else:
						self.close()
						self._cursor = cursor2
						self._con._usage += 1
						return result
					try:
						cursor2.close()
					except Exception:
						pass
				try: # try to reopen the connection
					con2 = self._con._create()
				except Exception:
					pass
				else:
					try:
						cursor2 = con2.cursor(
							*self._args, **self._kwargs) # open new cursor
					except Exception:
						pass
					else:
						try: # try one more time to execute
							if execute:
								self._setsizes(cursor2)
							method2 = getattr(cursor2, name)
							result = method2(*args, **kwargs)
							if execute:
								self._clearsizes()
						except Exception:
							pass
						else:
							self.close()
							self._con._close()
							self._con._store(con2)
							self._cursor = cursor2
							self._con._usage += 1
							return result
						try:
							cursor2.close()
						except Exception:
							pass
					try:
						con2.close()
					except Exception:
						pass
				raise error # reraise the original error again
			else:
				self._con._usage += 1
				return result
		return tough_method

	def __getattr__(self, name):
		"""Inherit methods and attributes of underlying cursor."""
		if name.startswith('execute') or name.startswith('call'):
			# make execution methods "tough"
			return self._get_tough_method(name)
		else:
			return getattr(self._cursor, name)

	def __del__(self):
		"""Delete the steady cursor."""
		self.close() # make sure the cursor is closed
