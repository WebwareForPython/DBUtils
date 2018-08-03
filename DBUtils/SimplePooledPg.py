"""SimplePooledPg - a very simple classic PyGreSQL connection pool.

Implements a pool of threadsafe cached connections
to a PostgreSQL database which are transparently reused,
using the classic (not DB-API 2 compliant) PyGreSQL pg API.

This should result in a speedup for persistent applications
such as the "Webware for Python" AppServer.

For more information on PostgreSQL, see:
    https://www.postgresql.org/
For more information on PyGreSQL, see:
    http://www.pygresql.org
For more information on Webware for Python, see:
    https://cito.github.io/w4py/

Measures are taken to make the pool of connections threadsafe
regardless of the fact that the PyGreSQL pg module itself is
not threadsafe at the connection level.  Connections will never be
shared between threads, so you can safely use transactions.

Usage:

The idea behind SimplePooledPg is that it's completely transparent.
After you have established your connection pool, stating the
number of connections to be cached in the pool and the
connection parameters, e.g.

    from DBUtils.SimplePooledPg import PooledPg
    dbpool = PooledPg(5, host=..., database=..., user=..., ...)

you can demand database connections from that pool,

    db = dbpool.connection()

and use them just as if they were ordinary PyGreSQL pg API
connections.  It's really just a proxy class.

db.close() will return the connection to the pool, it will not
actually close it.  This is so your existing code works nicely.

Ideas for improvement:

* Do not create the maximum number of connections on startup
already, but only a certain number and the rest on demand.
* Detect and transparently reset "bad" connections.  The PyGreSQL
pg API provides a status attribute and a reset() method for that.
* Connections should have some sort of "maximum usage limit"
after which they should be automatically closed and reopened.
* Prefer or enforce thread affinity for the connections.

Please note that these and other ideas have been already
implemented in in PooledPg, a more sophisticated version
of SimplePooledPg.  You might also consider using PersistentPg
instead for thread-affine persistent PyGreSQL connections.
SimplePooledPg may still serve as a very simple reference
and example implementation for developers.


Copyright, credits and license:

* Contributed as supplement for Webware for Python and PyGreSQL
  by Christoph Zwerschke in September 2005
* Based on the code of DBPool, contributed to Webware for Python
  by Dan Green in December 2000

Licensed under the MIT license.

"""

from pg import DB as PgConnection

__version__ = '1.3'


class PooledPgConnection:
    """A proxy class for pooled PostgreSQL connections.

    You don't normally deal with this class directly,
    but use PooledPg to get new connections.

    """

    def __init__(self, pool, con):
        self._con = con
        self._pool = pool

    def close(self):
        """Close the pooled connection."""
        # Instead of actually closing the connection,
        # return it to the pool so it can be reused.
        if self._con is not None:
            self._pool.cache(self._con)
            self._con = None

    def __getattr__(self, name):
        # All other members are the same.
        return getattr(self._con, name)

    def __del__(self):
        self.close()


class PooledPg:
    """A very simple PostgreSQL connection pool.

    After you have created the connection pool,
    you can get connections using getConnection().

    """

    version = __version__

    def __init__(self, maxconnections, *args, **kwargs):
        """Set up the PostgreSQL connection pool.

        maxconnections: the number of connections cached in the pool
        args, kwargs: the parameters that shall be used to establish
            the PostgreSQL connections using pg.connect()

        """
        # Since there is no connection level safety, we
        # build the pool using the synchronized queue class
        # that implements all the required locking semantics.
        try:
            from Queue import Queue
        except ImportError:  # Python 3
            from queue import Queue
        self._queue = Queue(maxconnections)
        # Establish all database connections (it would be better to
        # only establish a part of them now, and the rest on demand).
        for i in range(maxconnections):
            self.cache(PgConnection(*args, **kwargs))

    def cache(self, con):
        """Add or return a connection to the pool."""
        self._queue.put(con)

    def connection(self):
        """Get a connection from the pool."""
        return PooledPgConnection(self, self._queue.get())
