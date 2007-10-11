"""PooledPg - pooling for classic PyGreSQL connections.

Implements a pool of steady, thread-safe cached connections
to a PostgreSQL database which are transparently reused,
using the classic (not DB-API 2 compliant) PyGreSQL API.

This should result in a speedup for persistent applications such as the
application server of "Webware for Python," without loss of robustness.

Robustness is provided by using "hardened" SteadyPg connections.
Even if the underlying database is restarted and all connections
are lost, they will be automatically and transparently reopened.

Measures are taken to make the pool of connections thread-safe
regardless of the fact that the classic PyGreSQL pg module itself
is not thread-safe at the connection level.

For more information on PostgreSQL, see:
	http://www.postgresql.org
For more information on PyGreSQL, see:
	http://www.pygresql.org
For more information on Webware for Python, see:
	http://www.webwareforpython.org


Usage:

First you need to set up the database connection pool by creating
an instance of PooledPg, passing the following parameters:

	mincached: the initial number of connections in the pool
		(the default of 0 means no connections are made at startup)
	maxcached: the maximum number of connections in the pool
		(the default value of 0 means unlimited pool size)
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
	PostgreSQL connection which are passed via PyGreSQL,
	such as the names of the host, database, user, password etc.

For instance, if you want a pool of at least five connections
to your local database 'mydb':

	from DBUtils.PooledPg import PooledPg
	pool = PooledPg(5, dbname='mydb')

Once you have set up the connection pool you can request
database connections from that pool:

	db = pool.connection()

You can use these connections just as if they were ordinary
classic PyGreSQL API connections. Actually what you get is a
proxy class for the hardened SteadyPg version of the connection.

The connection will not be shared with other threads. If you don't need
it any more, you should immediately return it to the pool with db.close().
You can get another connection in the same way or with db.reopen().

Warning: In a threaded environment, never do the following:

	res = pool.connection().query(...).getresult()

This would release the connection too early for reuse which may be
fatal because the connections are not thread-safe. Make sure that the
connection object stays alive as long as you are using it, like that:

	db = pool.connection()
	res = db.query(...).getresult()
	db.close() # or del db


Ideas for improvement:

* Add a thread for monitoring, restarting (or closing) bad or expired
  connections (similar to DBConnectionPool/ResourcePool by Warren Smith).
* Optionally log usage, bad connections and exceeding of limits.


Copyright, credits and license:

* Contributed as supplement for Webware for Python and PyGreSQL
  by Christoph Zwerschke in September 2005
* Based on the code of DBPool, contributed to Webware for Python
  by Dan Green in December 2000

Licensed under the Open Software License version 2.1.

"""

__version__ = '0.9.4'
__revision__ = "$Rev$"
__date__ = "$Date$"


from Queue import Queue, Empty, Full

from DBUtils.SteadyPg import SteadyPgConnection

class PooledPgError(Exception):
	"""General PooledPg error."""

class InvalidConnection(PooledPgError):
	"""Database connection is invalid."""

class TooManyConnections(PooledPgError):
	"""Too many database connections were opened."""


class PooledPg:
	"""Pool for classic PyGreSQL connections.

	After you have created the connection pool, you can use
	connection() to get pooled, steady PostgreSQL connections.

	"""

	def __init__(self,
		mincached=0, maxcached=0,
		maxconnections=0, blocking=0,
		maxusage=0, setsession=None,
		*args, **kwargs):
		"""Set up the PostgreSQL connection pool.

		mincached: initial number of connections in the pool
			(0 means no connections are made at startup)
		maxcached: maximum number of connections in the pool
			(0 means unlimited pool size)
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
		self._args, self._kwargs = args, kwargs
		self._maxusage = maxusage
		self._setsession = setsession
		if maxcached:
			if maxcached < mincached:
				maxcached = mincached
		if maxconnections:
			if maxconnections < maxcached:
				maxconnections = maxcached
			# Create semaphore for number of allowed connections generally:
			from threading import Semaphore
			self._connections = Semaphore(maxconnections)
			self._blocking = blocking
		else:
			self._connections = None
		self._cache = Queue(maxcached) # the actual connection pool
		# Establish an initial number of database connections:
		[self.connection() for i in range(mincached)]

	def steady_connection(self):
		"""Get a steady, unpooled PostgreSQL connection."""
		return SteadyPgConnection(self._maxusage, self._setsession,
			*self._args, **self._kwargs)

	def connection(self):
		""""Get a steady, cached PostgreSQL connection from the pool."""
		if self._connections:
			if not self._connections.acquire(self._blocking):
				raise TooManyConnections
		try:
			con = self._cache.get(0)
		except Empty:
			con = self.steady_connection()
		return PooledPgConnection(self, con)

	def cache(self, con):
		"""Put a connection back into the pool cache."""
		try:
			self._cache.put(con, 0)
		except Full:
			con.close()
		if self._connections:
			self._connections.release()

	def close(self):
		"""Close all connections in the pool."""
		while 1:
			try:
				self._cache.get(0).close()
				if self._connections:
					self._connections.release()
			except Empty:
				break

	def __del__(self):
		"""Delete the pool."""
		self.close()


# Auxiliary class for pooled connections

class PooledPgConnection:
	"""Proxy class for pooled PostgreSQL connections."""

	def __init__(self, pool, con):
		"""Create a pooled DB-API 2 connection.

		pool: the corresponding PooledPg instance
		con: the underlying SteadyPg connection

		"""
		self._pool = pool
		self._con = con

	def close(self):
		"""Close the pooled connection."""
		# Instead of actually closing the connection,
		# return it to the pool so it can be reused.
		if self._con:
			self._pool.cache(self._con)
			self._con = None

	def reopen(self):
		"""Reopen the pooled connection."""
		# If the connection is already back in the pool,
		# get another connection from the pool,
		# otherwise reopen the unerlying connection.
		if self._con:
			self._con.reopen()
		else:
			self._con = self._pool.connection()

	def __getattr__(self, name):
		"""Proxy all members of the class."""
		if self._con:
			return getattr(self._con, name)
		else:
			raise InvalidConnection

	def __del__(self):
		"""Delete the pooled connection."""
		self.close()
