"""PersistentDB - persistent DB-API 2 connections.

Implements steady, thread-affine persistent connections to a database
based on an arbitrary DB-API 2 compliant database interface module.

This should result in a speedup for persistent applications such as the
application server of "Webware for Python," without loss of robustness.

Robustness is provided by using "hardened" SteadyDB connections.
Even if the underlying database is restarted and all connections
are lost, they will be automatically and transparently reopened.
However, since you don't want this to happen in the middle of a database
transaction, you must explicitly start transactions with the begin()
method so that SteadyDB knows that the underlying connection shall not
be replaced and errors passed on until the transaction is completed.

Measures are taken to make the database connections thread-affine.
This means the same thread always uses the same cached connection,
and no other thread will use it.  So even if the underlying DB-API module
is not thread-safe at the connection level this will be no problem here.

For best performance, the application server should keep threads persistent.
For this, you have to set MinServerThreads = MaxServerThreads in Webware.

For the Python DB-API 2 specification, see:
    https://www.python.org/dev/peps/pep-0249/
For information on Webware for Python, see:
    https://cito.github.io/w4py/


Usage:

First you need to set up a generator for your kind of database connections
by creating an instance of PersistentDB, passing the following parameters:

    creator: either an arbitrary function returning new DB-API 2
        connection objects or a DB-API 2 compliant database module
    maxusage: the maximum number of reuses of a single connection
        (the default of 0 or None means unlimited reuse)
        Whenever the limit is reached, the connection will be reset.
    setsession: an optional list of SQL commands that may serve to
        prepare the session, e.g. ["set datestyle to german", ...].
    failures: an optional exception class or a tuple of exception classes
        for which the connection failover mechanism shall be applied,
        if the default (OperationalError, InternalError) is not adequate
    ping: an optional flag controlling when connections are checked
        with the ping() method if such a method is available
        (0 = None = never, 1 = default = whenever it is requested,
        2 = when a cursor is created, 4 = when a query is executed,
        7 = always, and all other bit combinations of these values)
    closeable: if this is set to true, then closing connections will
        be allowed, but by default this will be silently ignored
    threadlocal: an optional class for representing thread-local data
        that will be used instead of our Python implementation
        (threading.local is faster, but cannot be used in all cases)

    The creator function or the connect function of the DB-API 2 compliant
    database module specified as the creator will receive any additional
    parameters such as the host, database, user, password etc.  You may
    choose some or all of these parameters in your own creator function,
    allowing for sophisticated failover and load-balancing mechanisms.

For instance, if you are using pgdb as your DB-API 2 database module and want
every connection to your local database 'mydb' to be reused 1000 times:

    import pgdb  # import used DB-API 2 module
    from DBUtils.PersistentDB import PersistentDB
    persist = PersistentDB(pgdb, 1000, database='mydb')

Once you have set up the generator with these parameters, you can
request database connections of that kind:

    db = persist.connection()

You can use these connections just as if they were ordinary
DB-API 2 connections.  Actually what you get is the hardened
SteadyDB version of the underlying DB-API 2 connection.

Closing a persistent connection with db.close() will be silently
ignored since it would be reopened at the next usage anyway and
contrary to the intent of having persistent connections.  Instead,
the connection will be automatically closed when the thread dies.
You can change this behavior be setting the closeable parameter.

Note that you need to explicitly start transactions by calling the
begin() method.  This ensures that the transparent reopening will be
suspended until the end of the transaction, and that the connection
will be rolled back before being reused by the same thread.

By setting the threadlocal parameter to threading.local, getting
connections may become a bit faster, but this may not work in all
environments (for instance, mod_wsgi is known to cause problems
since it clears the threading.local data between requests).


Requirements:

Python >= 2.6.


Ideas for improvement:

* Add a thread for monitoring, restarting (or closing) bad or expired
  connections (similar to DBConnectionPool/ResourcePool by Warren Smith).
* Optionally log usage, bad connections and exceeding of limits.


Copyright, credits and license:

* Contributed as supplement for Webware for Python and PyGreSQL
  by Christoph Zwerschke in September 2005
* Based on an idea presented on the Webware developer mailing list
  by Geoffrey Talvola in July 2005

Licensed under the MIT license.

"""

from DBUtils.SteadyDB import connect

__version__ = '1.3'

try:
    # Prefer the pure Python version of threading.local.
    # The C implementation turned out to be problematic with mod_wsgi,
    # since it does not keep the thread-local data between requests.
    from _threading_local import local
except ImportError:
    # Fall back to the default version of threading.local.
    from threading import local


class PersistentDBError(Exception):
    """General PersistentDB error."""


class NotSupportedError(PersistentDBError):
    """DB-API module not supported by PersistentDB."""


class PersistentDB:
    """Generator for persistent DB-API 2 connections.

    After you have created the connection pool, you can use
    connection() to get thread-affine, steady DB-API 2 connections.

    """

    version = __version__

    def __init__(
            self, creator,
            maxusage=None, setsession=None, failures=None, ping=1,
            closeable=False, threadlocal=None, *args, **kwargs):
        """Set up the persistent DB-API 2 connection generator.

        creator: either an arbitrary function returning new DB-API 2
            connection objects or a DB-API 2 compliant database module
        maxusage: maximum number of reuses of a single connection
            (number of database operations, 0 or None means unlimited)
            Whenever the limit is reached, the connection will be reset.
        setsession: optional list of SQL commands that may serve to prepare
            the session, e.g. ["set datestyle to ...", "set time zone ..."]
        failures: an optional exception class or a tuple of exception classes
            for which the connection failover mechanism shall be applied,
            if the default (OperationalError, InternalError) is not adequate
        ping: determines when the connection should be checked with ping()
            (0 = None = never, 1 = default = whenever it is requested,
            2 = when a cursor is created, 4 = when a query is executed,
            7 = always, and all other bit combinations of these values)
        closeable: if this is set to true, then closing connections will
            be allowed, but by default this will be silently ignored
        threadlocal: an optional class for representing thread-local data
            that will be used instead of our Python implementation
            (threading.local is faster, but cannot be used in all cases)
        args, kwargs: the parameters that shall be passed to the creator
            function or the connection constructor of the DB-API 2 module

        """
        try:
            threadsafety = creator.threadsafety
        except AttributeError:
            try:
                if not callable(creator.connect):
                    raise AttributeError
            except AttributeError:
                threadsafety = 1
            else:
                threadsafety = 0
        if not threadsafety:
            raise NotSupportedError("Database module is not thread-safe.")
        self._creator = creator
        self._maxusage = maxusage
        self._setsession = setsession
        self._failures = failures
        self._ping = ping
        self._closeable = closeable
        self._args, self._kwargs = args, kwargs
        self.thread = (threadlocal or local)()

    def steady_connection(self):
        """Get a steady, non-persistent DB-API 2 connection."""
        return connect(
            self._creator, self._maxusage, self._setsession,
            self._failures, self._ping, self._closeable,
            *self._args, **self._kwargs)

    def connection(self, shareable=False):
        """Get a steady, persistent DB-API 2 connection.

        The shareable parameter exists only for compatibility with the
        PooledDB connection method.  In reality, persistent connections
        are of course never shared with other threads.

        """
        try:
            con = self.thread.connection
        except AttributeError:
            con = self.steady_connection()
            if not con.threadsafety():
                raise NotSupportedError("Database module is not thread-safe.")
            self.thread.connection = con
        con._ping_check()
        return con

    def dedicated_connection(self):
        """Alias for connection(shareable=False)."""
        return self.connection()
