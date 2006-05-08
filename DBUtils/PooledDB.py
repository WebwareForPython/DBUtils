"""PooledDB - pooling for DB-API 2 connections.

Implements a pool of solid, thread-safe cached connections
to a database which are transparently reused,
using an arbitrary DB-API 2 compliant database interface module.

This should result in a speedup for persistent applications such as the
application server of "Webware for Python," without loss of robustness.

Robustness is provided by using "hardened" SolidDB connections.
Even if the underlying database is restarted and all connections
are lost, they will be automatically and transparently reopened.

Measures are taken to make the pool of connections thread-safe.
If the underlying DB-API module is thread-safe at the connection level,
the requested connections may be shared with other threads by default,
but you can also request dedicated connections in case you need them.

For the Python DB-API 2 specification, see:
	http://www.python.org/peps/pep-0249.html
For information on Webware for Python, see:
	http://www.webwareforpython.org


Usage:

First you need to set up the database connection pool by creating
an instance of PooledDB, passing the following parameters:

	dbapi: the DB-API 2 compliant database module to be used
	mincached: the initial number of idle connections in the pool
		(the default of 0 means no connections are made at startup)
	maxcached: the maximum number of idle connections in the pool
		(the default value of 0 means unlimited pool size)
	maxshared: maximum number of shared connections allowed
		(the default value of 0 means all connections are dedicated)
		When this maximum number is reached, connections are
		shared if they have been requested as shareable.
	maxconnections: maximum number of connections generally allowed
		(the default value of 0 means any number of connections)
	blocking: determines behavior when exceeding the maximum
		(the default of 0 or False means report an error; otherwise
		block and wait until the number of connections decreases)
	maxusage: maximum number of reuses of a single connection
		(the default of 0 or False means unlimited reuse)
		When this maximum usage number of the connection is reached,
		the connection is automatically reset (closed and reopened).
	setsession: an optional list of SQL commands that may serve to
		prepare the session, e.g. ["set datestyle to german", ...]

	Additionally, you have to pass the parameters for the actual
	database connection which are passed via the DB-API 2 module,
	such as the names of the host, database, user, password etc.

For instance, if you are using pgdb as your DB-API 2 database module and
want a pool of at least five connections to your local database 'mydb':

	import pgdb # import used DB-API 2 module
	from PooledDB import PooledDB
	pool = PooledPg(pgdb, 5, database='mydb')

Once you have set up the connection pool you can request
database connections from that pool:

	db = pool.connection()

You can use these connections just as if they were ordinary
DB-API 2 connections. Actually what you get is the hardened
SolidDB version of the underlying DB-API 2 connection.

Please note that the connection may be shared with other threads
by default if you set a non-zero maxshared parameter and the DB-API 2
module allows this. If you want to have a dedicated connection, use:

	db = pool.connection(0)

If you don't need it any more, you should immediately return it to the
pool with db.close(). You can get another connection in the same way.

Warning: In a threaded environment, never do the following:

	pool.connection().cursor().execute(...)

This would release the connection too early for reuse which may be
fatal if the connections are not thread-safe. Make sure that the
connection object stays alive as long as you are using it, like that:

	db = pool.connection()
	cur = db.cursor()
	cur.execute(...)
	res = cur.fetchone()
	cur.close() # or del cur
	db.close() # or del db


Ideas for improvement:

* Add thread for monitoring and restarting bad or expired connections
  (similar to DBConnectionPool/ResourcePool by Warren Smith).
* Optionally log usage, bad connections and exceeding of limits.


Copyright, credits and license:

* Contributed as supplement for Webware for Python and PyGreSQL
  by Christoph Zwerschke in September 2005
* Based on the code of DBPool, contributed to Webware for Python
  by Dan Green in December 2000

Licensed under the Open Software License version 2.1.

"""

__version__ = '0.9.1'
__revision__ = "$Rev$"
__date__ = "$Date$"


from SolidDB import connect
from threading import Condition

class PooledDBError(Exception): pass
class NotSupportedError(PooledDBError): pass
class TooManyConnections(PooledDBError): pass
class InvalidConnection(PooledDBError): pass


class PooledDB:
	"""Pool for classic PyGreSQL connections.

	After you have created the connection pool, you can use
	connection() to get pooled, solid PostGreSQL connections.

	"""

	def __init__(self, dbapi,
		mincached=0, maxcached=0,
		maxshared=0, maxconnections=0, blocking=0,
		maxusage=0, setsession=None,
		*args, **kwargs):
		"""Set up the PostgreSQL connection pool.

		dbapi: the DB-API 2 compliant database module to be used
		mincached: initial number of idle connections in the pool
			(0 means no connections are made at startup)
		maxcached: maximum number of idle connections in the pool
			(0 means unlimited pool size)
		maxshared: maximum number of shared connections
			(0 means all connections are dedicated)
			When this maximum number is reached, connections are
			shared if they have been requested as shareable.
		maxconnections: maximum number of connections generally allowed
			(0 means an arbitrary number of connections)
		blocking: determines behavior when exceeding the maximum
			(0 or False means report an error; otherwise
			block and wait until the number of connections decreases)
		maxusage: maximum number of reuses of a single connection
			(0 or False means unlimited reuse)
			When this maximum usage number of the connection is reached,
			the connection is automatically reset (closed and reopened).
		setsession: optional list of SQL commands that may serve to prepare
			the session, e.g. ["set datestyle to ...", "set time zone ..."]
		args, kwargs: the parameters that shall be used to establish
			the PostgreSQL connections using class PyGreSQL pg.DB()

		"""
		self._dbapi = dbapi
		# Connections can be only shareable if the underlying DB-API 2
		# module is thread-safe at the connection level:
		threadsafety = getattr(dbapi, 'threadsafety', None)
		if not threadsafety:
			raise NotSupportedError, "Database module is not thread-safe."
		self._args, self._kwargs = args, kwargs
		self._maxusage = maxusage
		self._setsession = setsession
		if maxcached:
			if maxcached < mincached:
				maxcached = mincached
			self._maxcached = maxcached
		else:
			self._maxcached = 0
		if threadsafety > 1 and maxshared:
			self._maxshared = maxshared
			self._shared_cache = [] # the cache for shared connections
		else:
			self._maxshared = 0
		if maxconnections:
			if maxconnections < maxcached:
				maxconnections = maxcached
			if maxconnections < maxshared:
				maxconnections = maxshared
			self._maxconnections = maxconnections
		else:
			self._maxconnections = 0
		self._idle_cache = [] # the actual pool of idle connections
		self._connections = 0
		self._condition = Condition()
		if not blocking:
			def wait():
				raise TooManyConnections
			self._condition.wait = wait
		# Establish an initial number of idle database connections:
		[self.connection(0) for i in range(mincached)]

	def solid_connection(self):
		"""Get a solid, unpooled solid DB-API 2 connection."""
		return connect(self._dbapi,
			self._maxusage, self._setsession, *self._args, **self._kwargs)

	def connection(self, shareable=1):
		""""Get a solid, cached DB-API 2 connection from the pool.

		If shareable is set and the underlying DB-API 2 allows it,
		then the connection may be shared with other threads.

		"""
		if shareable and self._maxshared:
			self._condition.acquire()
			try:
				while not self._shared_cache and self._maxconnections \
					and self._connections >= self._maxconnections:
					self._condition.wait()
				if len(self._shared_cache) < self._maxshared:
					# shared cache is not full, get a dedicated connection
					try: # first try to get it from the idle cache
						con = self._idle_cache.pop(0)
					except IndexError: # else get a fresh connection
						con = self.solid_connection()
					con = SharedDBConnection(con)
					self._connections += 1
				else: # shared cache full or no more connections allowed
					self._shared_cache.sort() # least shared connection first
					con = self._shared_cache.pop(0) # get it
					con.share() # increase share of this connection
				# put the connection (back) into the shared cache
				self._shared_cache.append(con)
				self._condition.notify()
			finally:
				self._condition.release()
			con = PooledSharedDBConnection(self, con)
		else: # try to get a dedicated connection
			self._condition.acquire()
			try:
				while self._maxconnections \
					and self._connections >= self._maxconnections:
					self._condition.wait()
				# connection limit not reached, get a dedicated connection
				try: # first try to get it from the idle cache
					con = self._idle_cache.pop(0)
				except IndexError: # else get a fresh connection
					con = self.solid_connection()
				con = PooledDedicatedDBConnection(self, con)
				self._connections += 1
			finally:
				self._condition.release()
		return con

	def unshare(self, con):
		"""Decrease the share of a connection in the shared cache."""
		self._condition.acquire()
		try:
			con.unshare()
			shared = con.shared
			if not shared: # connection is idle,
				try: # so try to remove it
					self._shared_cache.remove(con) # from shared cache
				except ValueError:
					pass # pool has already been closed
		finally:
			self._condition.release()
		if not shared: # connection has become idle,
			self.cache(con.con) # so add it to the idle cache

	def cache(self, con):
		"""Put a dedicated connection back into the idle cache."""
		self._condition.acquire()
		try:
			if not self._maxcached or len(self._idle_cache) < self._maxcached:
				# the idle cache is not full, so put it there, but
				try: # before returning the connection back to the pool,
					con.rollback() # perform a rollback
					# in order to prevent uncommited actions from being
					# unintentionally commited by some other thread
				except: # if an error occurs (no transaction, not supported)
					pass # then it will be silently ignored
				self._idle_cache.append(con) # append it to the idle cache
			else: # if the idle cache is already full,
				con.close() # then close the connection
			self._connections -= 1
			self._condition.notify()
		finally:
			self._condition.release()

	def close(self):
		"""Close all connections in the pool."""
		self._condition.acquire()
		try:
			while self._idle_cache: # close all idle connections
				self._idle_cache.pop(0).close()
				self._connections -= 1
			if self._maxshared: # close all shared connections
				while self._shared_cache:
					self._shared_cache.pop(0).con.close()
					self._connections -= 1
			self._condition.notifyAll()
		finally:
			self._condition.release()

	def __del__(self):
		"""Delete the pool."""
		if hasattr(self, '_connections'):
			self.close()


# Auxiliary classes for pooled connections

class PooledDedicatedDBConnection:
	"""Auxiliary proxy class for pooled dedicated connections."""

	def __init__(self, pool, con):
		"""Create a pooled dedicated connection.

		pool: the corresponding PooledDB instance
		con: the underlying SolidDB connection

		"""
		self._pool = pool
		self._con = con

	def close(self):
		"""Close the pooled dedicated connection."""
		# Instead of actually closing the connection,
		# return it to the pool for future reuse.
		if self._con:
			self._pool.cache(self._con)
			self._con = None

	def __getattr__(self, name):
		"""Proxy all members of the class."""
		if self._con:
			return getattr(self._con, name)
		else:
			raise InvalidConnection

	def __del__(self):
		"""Delete the pooled connection."""
		self.close()

class SharedDBConnection:
	"""Auxiliary class for shared connections."""

	def __init__(self, con):
		"""Create a shared connection.

		con: the underlying SolidDB connection

		"""
		self.con = con
		self.shared = 1

	def __cmp__(self, other):
		"""Compare how often the connections are shared."""
		return self.shared - other.shared

	def share(self):
		"""Increase the share of this connection."""
		self.shared += 1

	def unshare(self):
		"""Decrease the share of this connection."""
		self.shared -= 1

class PooledSharedDBConnection:
	"""Auxiliary proxy class for pooled shared connections."""

	def __init__(self, pool, shared_con):
		"""Create a pooled shared connection.

		pool: the corresponding PooledDB instance
		con: the underlying SharedDBConnection

		"""
		self._pool = pool
		self._shared_con = shared_con
		self._con = shared_con.con

	def close(self):
		"""Close the pooled shared connection."""
		# Instead of actually closing the connection,
		# unshare it and/or return it to the pool.
		if self._con:
			self._pool.unshare(self._shared_con)
			self._shared_con = self._con = None

	def __getattr__(self, name):
		"""Proxy all members of the class."""
		if self._con:
			return getattr(self._con, name)
		else:
			raise InvalidConnection

	def __del__(self):
		"""Delete the pooled connection."""
		self.close()
