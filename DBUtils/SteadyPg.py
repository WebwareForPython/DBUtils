"""SteadyPg - hardened classic PyGreSQL connections.

Implements steady connections to a PostgreSQL database
using the classic (not DB-API 2 compliant) PyGreSQL API.

The connections are transparently reopened when they are
closed or the database connection has been lost or when
they are used more often than an optional usage limit.

A typical situation where database connections are lost
is when the database server or an intervening firewall is
shutdown and restarted for maintenance reasons. In such a
case, all database connections would become unusuable, even
though the database service may be already available again.

The "hardened" connections provided by this module will
make the database connections immediately available again.

This results in a steady PostgreSQL connection that can be used
by PooledPg or PersistentPg to create pooled or persistent
connections to a PostgreSQL database in a threaded environment
such as the application server of "Webware for Python."
Note, however, that the connections themselves are not thread-safe.

For more information on PostgreSQL, see:
	http://www.postgresql.org
For more information on PyGreSQL, see:
	http://www.pygresql.org
For more information on Webware for Python, see:
	http://www.webwareforpython.org


Usage:

You can use the class SteadyPgConnection in the same way as you
would use the class DB from the classic PyGreSQL API module db.
The only difference is that you may specify a usage limit as the
first paramenter when you open a connection (set it to 0
if you prefer unlimited usage), and an optional list of commands
that may serve to prepare the session as the second parameter.
When the connection to the PostgreSQL database is lost or has been
used too often, it will be automatically reset, without further notice.

	from SteadyPg import SteadyPgConnection
	db = SteadyPgConnection(10000, ["set datestyle to german"],
		host=..., dbname=..., user=..., ...)
	...
	result = db.query('...')
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

__version__ = '0.9.2'
__revision__ = "$Rev$"
__date__ = "$Date$"


from pg import DB as PgConnection


class SteadyPgConnection:
	"""Class representing steady connections to a PostgreSQL database.

	Underlying the connection is a classic PyGreSQL pg API database
	connection which is reset if the connection is lost or used too often.
	Thus the resulting connection is steadier ("tough and self-healing").

	If you want the connection to be persistent in a threaded environment,
	then you should not deal with this class directly, but use either the
	PooledPg module or the PersistentPg module to get the connections.

	"""

	def __init__(self, maxusage=0, setsession=None, *args, **kwargs):
		"""Create a "tough" PostgreSQL connection.

		maxusage: maximum usage limit for the underlying PygreSQL connection
			(number of uses, 0 or False means unlimited usage)
			When this limit is reached, the connection is automatically reset.
		setsession: optional list of SQL commands that may serve to prepare
			the session, e.g. ["set datestyle to ...", "set time zone ..."]
		args, kwargs: the parameters that shall be used to establish
			the PostgreSQL connections with PyGreSQL using pg.DB()

		"""
		self._maxusage = maxusage
		self._setsession_sql = setsession
		self._closeable = 1
		self._usage = 0
		self._con = PgConnection(*args, **kwargs)
		self._setsession()

	def _setsession(self):
		"""Execute the SQL commands for session preparation."""
		if self._setsession_sql:
			for sql in self._setsession_sql:
				self._con.query(sql)

	def _close(self):
		"""Close the tough connection.

		You can always close a tough connection with this method
		and it will not complain if you close it more than once.

		"""
		try:
			self._con.close()
			self._usage = 0
		except:
			pass

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

	def reopen(self):
		"""Reopen the tough connection.

		It will not complain if the connection cannot be reopened."""
		try:
			self._con.reopen()
			self._setsession()
			self._usage = 0
		except:
			pass

	def reset(self):
		"""Reset the tough connection.

		If a reset is not possible, tries to reopen the connection.
		It will not complain if the connection is already closed.

		"""
		try:
			self._con.reset()
			self._setsession()
			self._usage = 0
		except:
			self.reopen()

	def _get_tough_method(self, method):
		"""Return a "tough" version of a connection class method.

		The tough version checks whether the connection is bad (lost)
		and automatically and transparently tries to reset the connection
		if this is the case (for instance, the database has been restarted).

		"""
		def tough_method(*args, **kwargs):
			try: # check whether connection status is bad
				if not self._con.db.status:
					raise AttributeError
				if self._maxusage: # or connection used too often
					if self._usage >= self._maxusage:
						raise AttributeError
			except:
				self.reset() # then reset the connection
			try:
				r = method(*args, **kwargs) # try connection method
			except: # error in query
				if self._con.db.status: # if it was not a connection problem
					raise # then propagate the error
				else: # otherwise
					self.reset() # reset the connection
					r = method(*args, **kwargs) # and try one more time
			self._usage += 1
			return r
		return tough_method

	def __getattr__(self, name):
		"""Inherit the members of the standard connection class.

		Some methods are made "tougher" than in the standard version.

		"""
		attr = getattr(self._con, name)
		if name in ('query', 'get', 'insert', 'update', 'delete') \
			or name.startswith('get_'):
			attr = self._get_tough_method(attr)
		return attr
