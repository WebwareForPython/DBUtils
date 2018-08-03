"""PersistentPg - persistent classic PyGreSQL connections.

Implements steady, thread-affine persistent connections to a PostgreSQL
database using the classic (not DB-API 2 compliant) PyGreSQL API.

This should result in a speedup for persistent applications such as the
application server of "Webware for Python," without loss of robustness.

Robustness is provided by using "hardened" SteadyPg connections.
Even if the underlying database is restarted and all connections
are lost, they will be automatically and transparently reopened.
However, since you don't want this to happen in the middle of a database
transaction, you must explicitly start transactions with the begin()
method so that SteadyPg knows that the underlying connection shall not
be replaced and errors passed on until the transaction is completed.

Measures are taken to make the database connections thread-affine.
This means the same thread always uses the same cached connection,
and no other thread will use it.  So the fact that the classic PyGreSQL
pg module is not thread-safe at the connection level is no problem here.

For best performance, the application server should keep threads persistent.
For this, you have to set MinServerThreads = MaxServerThreads in Webware.

For more information on PostgreSQL, see:
    https://www.postgresql.org/
For more information on PyGreSQL, see:
    http://www.pygresql.org
For more information on Webware for Python, see:
    https://cito.github.io/w4py/


Usage:

First you need to set up a generator for your kind of database connections
by creating an instance of PersistentPg, passing the following parameters:

    maxusage: the maximum number of reuses of a single connection
        (the default of 0 or None means unlimited reuse)
        When this maximum usage number of the connection is reached,
        the connection is automatically reset (closed and reopened).
    setsession: An optional list of SQL commands that may serve to
        prepare the session, e.g. ["set datestyle to german", ...]
    closeable: if this is set to true, then closing connections will
        be allowed, but by default this will be silently ignored
    threadlocal: an optional class for representing thread-local data
        that will be used instead of our Python implementation
        (threading.local is faster, but cannot be used in all cases)

    Additionally, you have to pass the parameters for the actual
    PostgreSQL connection which are passed via PyGreSQL,
    such as the names of the host, database, user, password etc.

For instance, if you want every connection to your local database 'mydb'
to be reused 1000 times:

    from DBUtils.PersistentPg import PersistentPg
    persist = PersistentPg(5, dbname='mydb')

Once you have set up the generator with these parameters, you can
request database connections of that kind:

    db = persist.connection()

You can use these connections just as if they were ordinary
classic PyGreSQL API connections.  Actually what you get is the
hardened SteadyPg version of a classic PyGreSQL connection.

Closing a persistent connection with db.close() will be silently
ignored since it would be reopened at the next usage anyway and
contrary to the intent of having persistent connections.  Instead,
the connection will be automatically closed when the thread dies.
You can change this behavior be setting the closeable parameter.

Note that you need to explicitly start transactions by calling the
begin() method.  This ensures that the transparent reopening will be
suspended until the end of the transaction, and that the connection
will be rolled back before being reused in the same thread.  To end
transactions, use one of the end(), commit() or rollback() methods.

By setting the threadlocal parameter to threading.local, getting
connections may become a bit faster, but this may not work in all
environments (for instance, mod_wsgi is known to cause problems
since it clears the threading.local data between requests).


Requirements:

Python >= 2.6, PyGreSQL >= 3.4.


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

from DBUtils.SteadyPg import SteadyPgConnection

__version__ = '1.3'

try:
    # Prefer the pure Python version of threading.local.
    # The C implementation turned out to be problematic with mod_wsgi,
    # since it does not keep the thread-local data between requests.
    from _threading_local import local
except ImportError:
    # Fall back to the default version of threading.local.
    from threading import local


class PersistentPg:
    """Generator for persistent classic PyGreSQL connections.

    After you have created the connection pool, you can use
    connection() to get thread-affine, steady PostgreSQL connections.

    """

    version = __version__

    def __init__(
            self, maxusage=None, setsession=None,
            closeable=False, threadlocal=None, *args, **kwargs):
        """Set up the persistent PostgreSQL connection generator.

        maxusage: maximum number of reuses of a single connection
            (0 or None means unlimited reuse)
            When this maximum usage number of the connection is reached,
            the connection is automatically reset (closed and reopened).
        setsession: optional list of SQL commands that may serve to prepare
            the session, e.g. ["set datestyle to ...", "set time zone ..."]
        closeable: if this is set to true, then closing connections will
            be allowed, but by default this will be silently ignored
        threadlocal: an optional class for representing thread-local data
            that will be used instead of our Python implementation
            (threading.local is faster, but cannot be used in all cases)
        args, kwargs: the parameters that shall be used to establish
            the PostgreSQL connections using class PyGreSQL pg.DB()

        """
        self._maxusage = maxusage
        self._setsession = setsession
        self._closeable = closeable
        self._args, self._kwargs = args, kwargs
        self.thread = (threadlocal or local)()

    def steady_connection(self):
        """Get a steady, non-persistent PyGreSQL connection."""
        return SteadyPgConnection(
            self._maxusage, self._setsession, self._closeable,
            *self._args, **self._kwargs)

    def connection(self):
        """Get a steady, persistent PyGreSQL connection."""
        try:
            con = self.thread.connection
        except AttributeError:
            con = self.steady_connection()
            self.thread.connection = con
        return con
