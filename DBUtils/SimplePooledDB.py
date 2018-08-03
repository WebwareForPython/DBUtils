"""SimplePooledDB - a very simple DB-API 2 database connection pool.

Implements a pool of threadsafe cached DB-API 2 connections
to a database which are transparently reused.

This should result in a speedup for persistent applications
such as the "Webware for Python" AppServer.

For more information on the DB-API 2, see:
    https://www.python.org/dev/peps/pep-0249/
For more information on Webware for Python, see:
    https://cito.github.io/w4py/

Measures are taken to make the pool of connections threadsafe
regardless of whether the DB-API 2 module used is threadsafe
on the connection level (threadsafety > 1) or not.  It must only
be threadsafe on the module level (threadsafety = 1).  If the
DB-API 2 module is threadsafe, the connections will be shared
between threads (keep this in mind if you use transactions).

Usage:

The idea behind SimplePooledDB is that it's completely transparent.
After you have established your connection pool, stating the
DB-API 2 module to be used, the number of connections
to be cached in the pool and the connection parameters, e.g.

    import pgdb  # import used DB-API 2 module
    from DBUtils.SimplePooledDB import PooledDB
    dbpool = PooledDB(pgdb, 5, host=..., database=..., user=..., ...)

you can demand database connections from that pool,

    db = dbpool.connection()

and use them just as if they were ordinary DB-API 2 connections.
It's really just a proxy class.

db.close() will return the connection to the pool, it will not
actually close it.  This is so your existing code works nicely.

Ideas for improvement:

* Do not create the maximum number of connections on startup
already, but only a certain number and the rest on demand.
* Detect and transparently reset "bad" connections.
* Connections should have some sort of maximum usage limit
after which they should be automatically closed and reopened.
* Prefer or enforce thread-affinity for the connections,
allowing for both sharable and non-sharable connections.

Please note that these and other ideas have been already
implemented in in PooledDB, a more sophisticated version
of SimplePooledDB.  You might also consider using PersistentDB
instead for thread-affine persistent database connections.
SimplePooledDB may still serve as a very simple reference
and example implementation for developers.


Copyright, credits and license:

* Contributed as MiscUtils/DBPool for Webware for Python
  by Dan Green, December 2000
* Thread safety bug found by Tom Schwaller
* Fixes by Geoff Talvola (thread safety in _threadsafe_getConnection())
* Clean up by Chuck Esterbrook
* Fix unthreadsafe functions which were leaking, Jay Love
* Eli Green's webware-discuss comments were lifted for additional docs
* Clean-up and detailed commenting, rename and move to DBUtils
  by Christoph Zwerschke in September 2005

Licensed under the MIT license.

"""

__version__ = '1.3'


class PooledDBError(Exception):
    """General PooledDB error."""


class NotSupportedError(PooledDBError):
    """DB-API module not supported by PooledDB."""


class PooledDBConnection:
    """A proxy class for pooled database connections.

    You don't normally deal with this class directly,
    but use PooledDB to get new connections.

    """

    def __init__(self, pool, con):
        self._con = con
        self._pool = pool

    def close(self):
        """Close the pooled connection."""
        # Instead of actually closing the connection,
        # return it to the pool so it can be reused.
        if self._con is not None:
            self._pool.returnConnection(self._con)
            self._con = None

    def __getattr__(self, name):
        # All other members are the same.
        return getattr(self._con, name)

    def __del__(self):
        self.close()


class PooledDB:
    """A very simple database connection pool.

    After you have created the connection pool,
    you can get connections using getConnection().

    """

    version = __version__

    def __init__(self, dbapi, maxconnections, *args, **kwargs):
        """Set up the database connection pool.

        dbapi: the DB-API 2 compliant module you want to use
        maxconnections: the number of connections cached in the pool
        args, kwargs: the parameters that shall be used to establish
            the database connections using connect()

        """
        try:
            threadsafety = dbapi.threadsafety
        except Exception:
            threadsafety = None
        if threadsafety == 0:
            raise NotSupportedError(
                "Database module does not support any level of threading.")
        elif threadsafety == 1:
            # If there is no connection level safety, build
            # the pool using the synchronized queue class
            # that implements all the required locking semantics.
            try:
                from Queue import Queue
            except ImportError:  # Python 3
                from queue import Queue
            self._queue = Queue(maxconnections)  # create the queue
            self.connection = self._unthreadsafe_get_connection
            self.addConnection = self._unthreadsafe_add_connection
            self.returnConnection = self._unthreadsafe_return_connection
        elif threadsafety in (2, 3):
            # If there is connection level safety, implement the
            # pool with an ordinary list used as a circular buffer.
            # We only need a minimum of locking in this case.
            from threading import Lock
            self._lock = Lock()  # create a lock object to be used later
            self._nextConnection = 0  # index of the next connection to be used
            self._connections = []  # the list of connections
            self.connection = self._threadsafe_get_connection
            self.addConnection = self._threadsafe_add_connection
            self.returnConnection = self._threadsafe_return_connection
        else:
            raise NotSupportedError(
                "Database module threading support cannot be determined.")
        # Establish all database connections (it would be better to
        # only establish a part of them now, and the rest on demand).
        for i in range(maxconnections):
            self.addConnection(dbapi.connect(*args, **kwargs))

    # The following functions are used with DB-API 2 modules
    # that do not have connection level threadsafety, like PyGreSQL.
    # However, the module must be threadsafe at the module level.
    # Note: threadsafe/unthreadsafe refers to the DB-API 2 module,
    # not to this class which should be threadsafe in any case.

    def _unthreadsafe_get_connection(self):
        """Get a connection from the pool."""
        return PooledDBConnection(self, self._queue.get())

    def _unthreadsafe_add_connection(self, con):
        """Add a connection to the pool."""
        self._queue.put(con)

    def _unthreadsafe_return_connection(self, con):
        """Return a connection to the pool.

        In this case, the connections need to be put
        back into the queue after they have been used.
        This is done automatically when the connection is closed
        and should never be called explicitly outside of this module.

        """
        self._unthreadsafe_add_connection(con)

    # The following functions are used with DB-API 2 modules
    # that are threadsafe at the connection level, like psycopg.
    # Note: In this case, connections are shared between threads.
    # This may lead to problems if you use transactions.

    def _threadsafe_get_connection(self):
        """Get a connection from the pool."""
        self._lock.acquire()
        try:
            next = self._nextConnection
            con = PooledDBConnection(self, self._connections[next])
            next += 1
            if next >= len(self._connections):
                next = 0
            self._nextConnection = next
            return con
        finally:
            self._lock.release()

    def _threadsafe_add_connection(self, con):
        """Add a connection to the pool."""
        self._connections.append(con)

    def _threadsafe_return_connection(self, con):
        """Return a connection to the pool.

        In this case, the connections always stay in the pool,
        so there is no need to do anything here.

        """
        pass
