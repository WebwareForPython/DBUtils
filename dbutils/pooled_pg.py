"""PooledPg - pooling for classic PyGreSQL connections.

Implements a pool of steady, thread-safe cached connections
to a PostgreSQL database which are transparently reused,
using the classic (not DB-API 2 compliant) PyGreSQL API.

This should result in a speedup for persistent applications such as the
application server of "Webware for Python," without loss of robustness.

Robustness is provided by using "hardened" SteadyPg connections.
Even if the underlying database is restarted and all connections
are lost, they will be automatically and transparently reopened.
However, since you don't want this to happen in the middle of a database
transaction, you must explicitly start transactions with the begin()
method so that SteadyPg knows that the underlying connection shall not
be replaced and errors passed on until the transaction is completed.

Measures are taken to make the pool of connections thread-safe
regardless of the fact that the classic PyGreSQL pg module itself
is not thread-safe at the connection level.

For more information on PostgreSQL, see:
    https://www.postgresql.org/
For more information on PyGreSQL, see:
    http://www.pygresql.org
For more information on Webware for Python, see:
    https://webwareforpython.github.io/w4py/


Usage:

First you need to set up the database connection pool by creating
an instance of PooledPg, passing the following parameters:

    mincached: the initial number of connections in the pool
        (the default of 0 means no connections are made at startup)
    maxcached: the maximum number of connections in the pool
        (the default value of 0 or None means unlimited pool size)
    maxconnections: maximum number of connections generally allowed
        (the default value of 0 or None means any number of connections)
    blocking: determines behavior when exceeding the maximum
        (if this is set to true, block and wait until the number of
        connections decreases, but by default an error will be reported)
    maxusage: maximum number of reuses of a single connection
        (the default of 0 or None means unlimited reuse)
        When this maximum usage number of the connection is reached,
        the connection is automatically reset (closed and reopened).
    setsession: an optional list of SQL commands that may serve to
        prepare the session, e.g. ["set datestyle to german", ...]

    Additionally, you have to pass the parameters for the actual
    PostgreSQL connection which are passed via PyGreSQL,
    such as the names of the host, database, user, password etc.

For instance, if you want a pool of at least five connections
to your local database 'mydb':

    from dbutils.pooled_pg import PooledPg
    pool = PooledPg(5, dbname='mydb')

Once you have set up the connection pool you can request
database connections from that pool:

    db = pool.connection()

You can use these connections just as if they were ordinary
classic PyGreSQL API connections.  Actually what you get is a
proxy class for the hardened SteadyPg version of the connection.

The connection will not be shared with other threads.  If you don't need
it anymore, you should immediately return it to the pool with db.close().
You can get another connection in the same way or with db.reopen().

Warning: In a threaded environment, never do the following:

    res = pool.connection().query(...).getresult()

This would release the connection too early for reuse which may be
fatal because the connections are not thread-safe.  Make sure that the
connection object stays alive as long as you are using it, like that:

    db = pool.connection()
    res = db.query(...).getresult()
    db.close()  # or del db

You can also a context manager for simpler code:

    with pool.connection() as db:
        res = db.query(...).getresult()

Note that you need to explicitly start transactions by calling the
begin() method.  This ensures that the transparent reopening will be
suspended until the end of the transaction, and that the connection will
be rolled back before being given back to the connection pool.  To end
transactions, use one of the end(), commit() or rollback() methods.


Ideas for improvement:

* Add a thread for monitoring, restarting (or closing) bad or expired
  connections (similar to DBConnectionPool/ResourcePool by Warren Smith).
* Optionally log usage, bad connections and exceeding of limits.


Copyright, credits and license:

* Contributed as supplement for Webware for Python and PyGreSQL
  by Christoph Zwerschke in September 2005
* Based on the code of DBPool, contributed to Webware for Python
  by Dan Green in December 2000

Licensed under the MIT license.
"""

from contextlib import suppress
from queue import Empty, Full, Queue

from . import __version__
from .steady_pg import SteadyPgConnection

__all__ = [
    'PooledPg', 'PooledPgConnection',
    'PooledPgError', 'InvalidConnectionError', 'TooManyConnectionsError',
    'RESET_ALWAYS_ROLLBACK', 'RESET_COMPLETELY',
]

# constants for "reset" parameter
RESET_ALWAYS_ROLLBACK = 1
RESET_COMPLETELY = 2


class PooledPgError(Exception):
    """General PooledPg error."""


class InvalidConnectionError(PooledPgError):
    """Database connection is invalid."""


class TooManyConnectionsError(PooledPgError):
    """Too many database connections were opened."""


# deprecated alias names for error classes
InvalidConnection = InvalidConnectionError
TooManyConnections = TooManyConnectionsError


class PooledPg:
    """Pool for classic PyGreSQL connections.

    After you have created the connection pool, you can use
    connection() to get pooled, steady PostgreSQL connections.
    """

    version = __version__

    def __init__(
            self, mincached=0, maxcached=0,
            maxconnections=0, blocking=False,
            maxusage=None, setsession=None, reset=None,
            *args, **kwargs):
        """Set up the PostgreSQL connection pool.

        mincached: initial number of connections in the pool
            (0 means no connections are made at startup)
        maxcached: maximum number of connections in the pool
            (0 or None means unlimited pool size)
        maxconnections: maximum number of connections generally allowed
            (0 or None means an arbitrary number of connections)
        blocking: determines behavior when exceeding the maximum
            (if this is set to true, block and wait until the number of
            connections decreases, otherwise an error will be reported)
        maxusage: maximum number of reuses of a single connection
            (0 or None means unlimited reuse)
            When this maximum usage number of the connection is reached,
            the connection is automatically reset (closed and reopened).
        setsession: optional list of SQL commands that may serve to prepare
            the session, e.g. ["set datestyle to ...", "set time zone ..."]
        reset: how connections should be reset when returned to the pool
            (0 or None to rollback transactions started with begin(),
            1 to always issue a rollback, 2 for a complete reset)
        args, kwargs: the parameters that shall be used to establish
            the PostgreSQL connections using class PyGreSQL pg.DB()
        """
        self._args, self._kwargs = args, kwargs
        self._maxusage = maxusage
        self._setsession = setsession
        self._reset = reset or 0
        if mincached is None:
            mincached = 0
        if maxcached is None:
            maxcached = 0
        if maxconnections is None:
            maxconnections = 0
        if maxcached and maxcached < mincached:
            maxcached = mincached
        if maxconnections:
            maxconnections = max(maxconnections, maxcached)
            # Create semaphore for number of allowed connections generally:
            from threading import Semaphore  # noqa: PLC0415
            self._connections = Semaphore(maxconnections)
            self._blocking = blocking
        else:
            self._connections = None
        self._cache = Queue(maxcached)  # the actual connection pool
        # Establish an initial number of database connections:
        idle = [self.connection() for i in range(mincached)]
        while idle:
            idle.pop().close()

    def steady_connection(self):
        """Get a steady, unpooled PostgreSQL connection."""
        return SteadyPgConnection(self._maxusage, self._setsession, True,
                                  *self._args, **self._kwargs)

    def connection(self):
        """Get a steady, cached PostgreSQL connection from the pool."""
        if self._connections and not self._connections.acquire(self._blocking):
            raise TooManyConnectionsError
        try:
            con = self._cache.get_nowait()
        except Empty:
            con = self.steady_connection()
        return PooledPgConnection(self, con)

    def cache(self, con):
        """Put a connection back into the pool cache."""
        try:
            if self._reset == RESET_COMPLETELY:
                con.reset()  # reset the connection completely
            elif self._reset == RESET_ALWAYS_ROLLBACK or con._transaction:
                with suppress(Exception):
                    con.rollback()  # rollback a possible transaction
            self._cache.put_nowait(con)  # and then put it back into the cache
        except Full:
            con.close()
        if self._connections:
            self._connections.release()

    def close(self):
        """Close all connections in the pool."""
        while 1:
            try:
                con = self._cache.get_nowait()
                with suppress(Exception):
                    con.close()
                if self._connections:
                    self._connections.release()
            except Empty:
                break

    def __del__(self):
        """Delete the pool."""
        # builtins (including Exceptions) might not exist anymore
        try:  # noqa: SIM105
            self.close()
        except:  # noqa: E722, S110
            pass


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
        # return it to the pool so that it can be reused.
        if self._con:
            self._pool.cache(self._con)
            self._con = None

    def reopen(self):
        """Reopen the pooled connection."""
        # If the connection is already back in the pool,
        # get another connection from the pool,
        # otherwise reopen the underlying connection.
        if self._con:
            self._con.reopen()
        else:
            self._con = self._pool.connection()

    def __getattr__(self, name):
        """Proxy all members of the class."""
        if self._con:
            return getattr(self._con, name)
        raise InvalidConnectionError

    def __del__(self):
        """Delete the pooled connection."""
        # builtins (including Exceptions) might not exist anymore
        try:  # noqa: SIM105
            self.close()
        except:  # noqa: E722, S110
            pass

    def __enter__(self):
        """Enter a runtime context for the connection."""
        return self

    def __exit__(self, *exc):
        """Exit a runtime context for the connection."""
        self.close()
