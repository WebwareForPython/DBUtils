"""PersistentDB - persistent DB-API 2 connections.

Implements solid, thread-affine persistent connections to a database
based on an arbitrary DB-API 2 compliant database interface module.

This should result in a speedup for persistent applications such as the
application server of "Webware for Python," without loss of robustness.

Robustness is provided by using "hardened" SolidDB connections.
Even if the underlying database is restarted and all connections
are lost, they will be automatically and transparently reopened.

Measures are taken to make the database connections thread-affine.
This means the same thread always uses the same cached connection,
and no other thread will use it. So even if the underlying DB-API module
is not thread-safe at the connection level this will be no problem here.

For best performance, the application server should keep threads persistent.
For this, you have to set MinServerThreads = MaxServerThreads in Webware.

For the Python DB-API 2 specification, see:
	http://www.python.org/peps/pep-0249.html
For information on Webware for Python, see:
	http://www.webwareforpython.org


Usage:

First you need to set up a generator for your kind of database connections
by creating an instance of PersistentDB, passing the following parameters:

	dbapi: the DB-API 2 compliant database module to be used
	maxusage: the maximum number of reuses of a single connection
		(the default of 0 or False means unlimited reuse)
		Whenever the limit is reached, the connection will be reset.
	setsession: an optional list of SQL commands that may serve to
		prepare the session, e.g. ["set datestyle to german", ...].

	Additionally, you have to pass the parameters for the actual
	database connection which are passed via the DB-API 2 module,
	such as the names of the host, database, user, password etc.

For instance, if you are using pgdb as your DB-API 2 database module and want
every connection to your local database 'mydb' to be reused 1000 times:

	import pgdb # import used DB-API 2 module
	from PersistentDB import PersistentDB
	persist = PersistentDB(pgdb, 1000, database='mydb')

Once you have set up the generator with these parameters, you can
request database connections of that kind:

	db = persist.connection()

You can use these connections just as if they were ordinary
DB-API 2 connections. Actually what you get is the hardened
SolidDB version of the underlying DB-API 2 connection.

Closing a persistent connection with db.close() will be silently
ignored since it would be reopened at the next usage anyway and
contrary to the intent of having persistent connections. Instead,
the connection will be automatically closed when the thread dies.
You can change this behavior be setting persist._closeable to True.


Requirements:

Minimum requirement: Python 2.2. Recommended: Python 2.4.3.


Ideas for improvement:

* Add thread for monitoring and restarting bad or expired connections
  (similar to DBConnectionPool/ResourcePool by Warren Smith).
* Optionally log usage, bad connections and exceeding of limits.


Copyright, credits and license:

* Contributed as supplement for Webware for Python and PyGreSQL
  by Christoph Zwerschke in September 2005
* Based on an idea presented on the Webware developer mailing list
  by Geoffrey Talvola in July 2005

Licensed under the Open Software License version 2.1.

"""

__version__ = '0.9.1'
__revision__ = "$Rev$"
__date__ = "$Date$"


from SolidDB import connect

class PersistentDBError(Exception): pass
class NotSupportedError(PersistentDBError): pass


class PersistentDB:
	"""Generator for persistent DB-API 2 connections.

	After you have created the connection pool, you can use
	connection() to get thread-affine, solid DB-API 2 connections.

	"""

	def __init__(self, dbapi,
		maxusage=0, setsession=None, *args, **kwargs):
		"""Set up the persistent DB-API 2 connection generator.

		dbapi: the DB-API 2 compliant database module to be used
		maxusage: maximum number of reuses of a single connection
			(number of database operations, 0 or False means unlimited)
			Whenever the limit is reached, the connection will be reset.
		setsession: optional list of SQL commands that may serve to prepare
			the session, e.g. ["set datestyle to ...", "set time zone ..."]
		args, kwargs: the parameters that shall be used to establish
			the database connections using the DB-API 2 module

		Set the _closeable attribute to True or 1 to allow closing
		connections. By default, this will be silently ignored.

		"""
		if not getattr(dbapi, 'threadsafety', None):
			raise NotSupportedError, "Database module is not thread-safe."
		self._dbapi = dbapi
		self._maxusage = maxusage
		self._setsession = setsession
		self._args, self._kwargs = args, kwargs
		self._closeable = 0
		self.thread = local()

	def solid_connection(self):
		"""Get a solid, non-persistent DB-API 2 connection."""
		return connect(self._dbapi,
			self._maxusage, self._setsession, *self._args, **self._kwargs)

	def connection(self, shareable=0):
		"""Get a solid, persistent DB-API 2 connection.

		The shareable parameter exists only for compatibility with the
		PooledDB connection method. In reality, persistent connections
		are of course never shared with other threads.

		"""
		if not hasattr(self.thread, 'connection'):
			self.thread.connection = self.solid_connection()
			self.thread.connection._closeable = self._closeable
		return self.thread.connection


try: # import a class for representing thread-local objects
	from threading import local
except: # for Python < 2.4, use the following simple implementation
	from threading import currentThread, enumerate, RLock
	class _localbase(object):
		__slots__ = '_local__key', '_local__args', '_local__lock'
		def __new__(cls, *args, **kw):
			self = object.__new__(cls)
			key = '_local__key', 'thread.local.' + str(id(self))
			object.__setattr__(self, '_local__key', key)
			object.__setattr__(self, '_local__args', (args, kw))
			object.__setattr__(self, '_local__lock', RLock())
			if args or kw and (cls.__init__ is object.__init__):
				raise TypeError("Initialization arguments are not supported")
			dict = object.__getattribute__(self, '__dict__')
			currentThread().__dict__[key] = dict
			return self
	def _patch(self):
		key = object.__getattribute__(self, '_local__key')
		d = currentThread().__dict__.get(key)
		if d is None:
			d = {}
			currentThread().__dict__[key] = d
			object.__setattr__(self, '__dict__', d)
			cls = type(self)
			if cls.__init__ is not object.__init__:
				args, kw = object.__getattribute__(self, '_local__args')
				cls.__init__(self, *args, **kw)
		else:
			object.__setattr__(self, '__dict__', d)
	class local(_localbase):
		def __getattribute__(self, name):
			lock = object.__getattribute__(self, '_local__lock')
			lock.acquire()
			try:
				_patch(self)
				return object.__getattribute__(self, name)
			finally:
				lock.release()
		def __setattr__(self, name, value):
			lock = object.__getattribute__(self, '_local__lock')
			lock.acquire()
			try:
				_patch(self)
				return object.__setattr__(self, name, value)
			finally:
				lock.release()
		def __delattr__(self, name):
			lock = object.__getattribute__(self, '_local__lock')
			lock.acquire()
			try:
				_patch(self)
				return object.__delattr__(self, name)
			finally:
				lock.release()
		def __del__():
			threading_enumerate = enumerate
			__getattribute__ = object.__getattribute__
			def __del__(self):
				key = __getattribute__(self, '_local__key')
				try:
					threads = list(threading_enumerate())
				except:
					return
				for thread in threads:
					try:
						__dict__ = thread.__dict__
					except AttributeError:
						continue
					if key in __dict__:
						try:
							del __dict__[key]
						except KeyError:
							pass
			return __del__
		__del__ = __del__()