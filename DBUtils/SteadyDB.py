"""SteadyDB - hardened DB-API 2 connections.

Implements steady connections to a database based on an
arbitrary DB-API 2 compliant database interface module.

The connections are transparently reopened when they are
closed or the database connection has been lost or when
they are used more often than an optional usage limit.
Database cursors are transparently reopened as well when
the execution of a database operation cannot be performed
due to a lost connection.  Only if the connection is lost
after the execution, when rows are already fetched from the
database, this will give an error and the cursor will not
be reopened automatically, because there is no reliable way
to recover the state of the cursor in such a situation.
Connections which have been marked as being in a transaction
with a begin() call will not be silently replaced either.

A typical situation where database connections are lost
is when the database server or an intervening firewall is
shutdown and restarted for maintenance reasons.  In such a
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
    https://www.python.org/dev/peps/pep-0249/
For information on Webware for Python, see:
    https://cito.github.io/w4py/

Usage:

You can use the connection constructor connect() in the same
way as you would use the connection constructor of a DB-API 2
module if you specify the DB-API 2 module to be used as the
first parameter, or alternatively you can specify an arbitrary
constructor function returning new DB-API 2 compliant connection
objects as the first parameter.  Passing just a function allows
implementing failover mechanisms and load balancing strategies.

You may also specify a usage limit as the second parameter
(set it to None if you prefer unlimited usage), an optional
list of commands that may serve to prepare the session as a
third parameter, the exception classes for which the failover
mechanism shall be applied, and you can specify whether is is
allowed to close the connection (by default this is true).
When the connection to the database is lost or has been used
too often, it will be transparently reset in most situations,
without further notice.

    import pgdb  # import used DB-API 2 module
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

Licensed under the MIT license.

"""

import sys

__version__ = '1.3'

try:
    baseint = (int, long)
except NameError:  # Python 3
    baseint = int


class SteadyDBError(Exception):
    """General SteadyDB error."""


class InvalidCursor(SteadyDBError):
    """Database cursor is invalid."""


def connect(
        creator, maxusage=None, setsession=None,
        failures=None, ping=1, closeable=True, *args, **kwargs):
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
    ping: determines when the connection should be checked with ping()
        (0 = None = never, 1 = default = when _ping_check() is called,
        2 = whenever a cursor is created, 4 = when a query is executed,
        7 = always, and all other bit combinations of these values)
    closeable: if this is set to false, then closing the connection will
        be silently ignored, but by default the connection can be closed
    args, kwargs: the parameters that shall be passed to the creator
        function or the connection constructor of the DB-API 2 module

    """
    return SteadyDBConnection(
        creator, maxusage, setsession,
        failures, ping, closeable, *args, **kwargs)


class SteadyDBConnection:
    """A "tough" version of DB-API 2 connections."""

    version = __version__

    def __init__(
            self, creator, maxusage=None, setsession=None,
            failures=None, ping=1, closeable=True, *args, **kwargs):
        """Create a "tough" DB-API 2 connection."""
        # basic initialization to make finalizer work
        self._con = None
        self._closed = True
        # proper initialization of the connection
        try:
            self._creator = creator.connect
            self._dbapi = creator
        except AttributeError:
            # try finding the DB-API 2 module via the connection creator
            self._creator = creator
            try:
                self._dbapi = creator.dbapi
            except AttributeError:
                try:
                    self._dbapi = sys.modules[creator.__module__]
                    if self._dbapi.connect != creator:
                        raise AttributeError
                except (AttributeError, KeyError):
                    self._dbapi = None
        try:
            self._threadsafety = creator.threadsafety
        except AttributeError:
            try:
                self._threadsafety = self._dbapi.threadsafety
            except AttributeError:
                self._threadsafety = None
        if not callable(self._creator):
            raise TypeError("%r is not a connection provider." % (creator,))
        if maxusage is None:
            maxusage = 0
        if not isinstance(maxusage, baseint):
            raise TypeError("'maxusage' must be an integer value.")
        self._maxusage = maxusage
        self._setsession_sql = setsession
        if failures is not None and not isinstance(
                failures, tuple) and not issubclass(failures, Exception):
            raise TypeError("'failures' must be a tuple of exceptions.")
        self._failures = failures
        self._ping = ping if isinstance(ping, int) else 0
        self._closeable = closeable
        self._args, self._kwargs = args, kwargs
        self._store(self._create())

    def __enter__(self):
        """Enter the runtime context for the connection object."""
        return self

    def __exit__(self, *exc):
        """Exit the runtime context for the connection object.

        This does not close the connection, but it ends a transaction.

        """
        if exc[0] is None and exc[1] is None and exc[2] is None:
            self.commit()
        else:
            self.rollback()

    def _create(self):
        """Create a new connection using the creator function."""
        con = self._creator(*self._args, **self._kwargs)
        try:
            try:
                if self._dbapi.connect != self._creator:
                    raise AttributeError
            except AttributeError:
                # try finding the DB-API 2 module via the connection itself
                try:
                    mod = con.__module__
                except AttributeError:
                    mod = None
                while mod:
                    try:
                        self._dbapi = sys.modules[mod]
                        if not callable(self._dbapi.connect):
                            raise AttributeError
                    except (AttributeError, KeyError):
                        pass
                    else:
                        break
                    i = mod.rfind('.')
                    if i < 0:
                        mod = None
                    else:
                        mod = mod[:i]
                else:
                    try:
                        mod = con.OperationalError.__module__
                    except AttributeError:
                        mod = None
                    while mod:
                        try:
                            self._dbapi = sys.modules[mod]
                            if not callable(self._dbapi.connect):
                                raise AttributeError
                        except (AttributeError, KeyError):
                            pass
                        else:
                            break
                        i = mod.rfind('.')
                        if i < 0:
                            mod = None
                        else:
                            mod = mod[:i]
                    else:
                        self._dbapi = None
            if self._threadsafety is None:
                try:
                    self._threadsafety = self._dbapi.threadsafety
                except AttributeError:
                    try:
                        self._threadsafety = con.threadsafety
                    except AttributeError:
                        pass
            if self._failures is None:
                try:
                    self._failures = (
                        self._dbapi.OperationalError,
                        self._dbapi.InternalError)
                except AttributeError:
                    try:
                        self._failures = (
                            self._creator.OperationalError,
                            self._creator.InternalError)
                    except AttributeError:
                        try:
                            self._failures = (
                                con.OperationalError, con.InternalError)
                        except AttributeError:
                            raise AttributeError(
                                "Could not determine failure exceptions"
                                " (please set failures or creator.dbapi).")
            if isinstance(self._failures, tuple):
                self._failure = self._failures[0]
            else:
                self._failure = self._failures
            self._setsession(con)
        except Exception as error:
            # the database module could not be determined
            # or the session could not be prepared
            try:  # close the connection first
                con.close()
            except Exception:
                pass
            raise error  # re-raise the original error again
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
        self._transaction = False
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
            self._transaction = False
            self._closed = True

    def _reset(self, force=False):
        """Reset a tough connection.

        Rollback if forced or the connection was in a transaction.

        """
        if not self._closed and (force or self._transaction):
            try:
                self.rollback()
            except Exception:
                pass

    def _ping_check(self, ping=1, reconnect=True):
        """Check whether the connection is still alive using ping().

        If the the underlying connection is not active and the ping
        parameter is set accordingly, the connection will be recreated
        unless the connection is currently inside a transaction.

        """
        if ping & self._ping:
            try:  # if possible, ping the connection
                alive = self._con.ping()
            except (AttributeError, IndexError, TypeError, ValueError):
                self._ping = 0  # ping() is not available
                alive = None
                reconnect = False
            except Exception:
                alive = False
            else:
                if alive is None:
                    alive = True
                if alive:
                    reconnect = False
            if reconnect and not self._transaction:
                try:  # try to reopen the connection
                    con = self._create()
                except Exception:
                    pass
                else:
                    self._close()
                    self._store(con)
                    alive = True
            return alive

    def dbapi(self):
        """Return the underlying DB-API 2 module of the connection."""
        if self._dbapi is None:
            raise AttributeError(
                "Could not determine DB-API 2 module"
                " (please set creator.dbapi).")
        return self._dbapi

    def threadsafety(self):
        """Return the thread safety level of the connection."""
        if self._threadsafety is None:
            if self._dbapi is None:
                raise AttributeError(
                    "Could not determine threadsafety"
                    " (please set creator.dbapi or creator.threadsafety).")
            return 0
        return self._threadsafety

    def close(self):
        """Close the tough connection.

        You are allowed to close a tough connection by default
        and it will not complain if you close it more than once.

        You can disallow closing connections by setting
        the closeable parameter to something false.  In this case,
        closing tough connections will be silently ignored.

        """
        if self._closeable:
            self._close()
        elif self._transaction:
            self._reset()

    def begin(self, *args, **kwargs):
        """Indicate the beginning of a transaction.

        During a transaction, connections won't be transparently
        replaced, and all errors will be raised to the application.

        If the underlying driver supports this method, it will be called
        with the given parameters (e.g. for distributed transactions).

        """
        self._transaction = True
        try:
            begin = self._con.begin
        except AttributeError:
            pass
        else:
            begin(*args, **kwargs)

    def commit(self):
        """Commit any pending transaction."""
        self._transaction = False
        try:
            self._con.commit()
        except self._failures as error:  # cannot commit
            try:  # try to reopen the connection
                con = self._create()
            except Exception:
                pass
            else:
                self._close()
                self._store(con)
            raise error  # re-raise the original error

    def rollback(self):
        """Rollback pending transaction."""
        self._transaction = False
        try:
            self._con.rollback()
        except self._failures as error:  # cannot rollback
            try:  # try to reopen the connection
                con = self._create()
            except Exception:
                pass
            else:
                self._close()
                self._store(con)
            raise error  # re-raise the original error

    def cancel(self):
        """Cancel a long-running transaction.

        If the underlying driver supports this method, it will be called.

        """
        self._transaction = False
        try:
            cancel = self._con.cancel
        except AttributeError:
            pass
        else:
            cancel()

    def ping(self, *args, **kwargs):
        """Ping connection."""
        return self._con.ping(*args, **kwargs)

    def _cursor(self, *args, **kwargs):
        """A "tough" version of the method cursor()."""
        # The args and kwargs are not part of the standard,
        # but some database modules seem to use these.
        transaction = self._transaction
        if not transaction:
            self._ping_check(2)
        try:
            if self._maxusage:
                if self._usage >= self._maxusage:
                    # the connection was used too often
                    raise self._failure
            cursor = self._con.cursor(*args, **kwargs)  # try to get a cursor
        except self._failures as error:  # error in getting cursor
            try:  # try to reopen the connection
                con = self._create()
            except Exception:
                pass
            else:
                try:  # and try one more time to get a cursor
                    cursor = con.cursor(*args, **kwargs)
                except Exception:
                    pass
                else:
                    self._close()
                    self._store(con)
                    if transaction:
                        raise error  # re-raise the original error again
                    return cursor
                try:
                    con.close()
                except Exception:
                    pass
            if transaction:
                self._transaction = False
            raise error  # re-raise the original error again
        return cursor

    def cursor(self, *args, **kwargs):
        """Return a new Cursor Object using the connection."""
        return SteadyDBCursor(self, *args, **kwargs)

    def __del__(self):
        """Delete the steady connection."""
        try:
            self._close()  # make sure the connection is closed
        except Exception:
            pass


class SteadyDBCursor:
    """A "tough" version of DB-API 2 cursors."""

    def __init__(self, con, *args, **kwargs):
        """Create a "tough" DB-API 2 cursor."""
        # basic initialization to make finalizer work
        self._cursor = None
        self._closed = True
        # proper initialization of the cursor
        self._con = con
        self._args, self._kwargs = args, kwargs
        self._clearsizes()
        try:
            self._cursor = con._cursor(*args, **kwargs)
        except AttributeError:
            raise TypeError("%r is not a SteadyDBConnection." % (con,))
        self._closed = False

    def __enter__(self):
        """Enter the runtime context for the cursor object."""
        return self

    def __exit__(self, *exc):
        """Exit the runtime context for the cursor object."""
        self.close()

    def setinputsizes(self, sizes):
        """Store input sizes in case cursor needs to be reopened."""
        self._inputsizes = sizes

    def setoutputsize(self, size, column=None):
        """Store output sizes in case cursor needs to be reopened."""
        self._outputsizes[column] = size

    def _clearsizes(self):
        """Clear stored input and output sizes."""
        self._inputsizes = []
        self._outputsizes = {}

    def _setsizes(self, cursor=None):
        """Set stored input and output sizes for cursor execution."""
        if cursor is None:
            cursor = self._cursor
        if self._inputsizes:
            cursor.setinputsizes(self._inputsizes)
        for column, size in self._outputsizes.items():
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
        """Return a "tough" version of the given cursor method."""
        def tough_method(*args, **kwargs):
            execute = name.startswith('execute')
            con = self._con
            transaction = con._transaction
            if not transaction:
                con._ping_check(4)
            try:
                if con._maxusage:
                    if con._usage >= con._maxusage:
                        # the connection was used too often
                        raise con._failure
                if execute:
                    self._setsizes()
                method = getattr(self._cursor, name)
                result = method(*args, **kwargs)  # try to execute
                if execute:
                    self._clearsizes()
            except con._failures as error:  # execution error
                if not transaction:
                    try:
                        cursor2 = con._cursor(
                            *self._args, **self._kwargs)  # open new cursor
                    except Exception:
                        pass
                    else:
                        try:  # and try one more time to execute
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
                            con._usage += 1
                            return result
                        try:
                            cursor2.close()
                        except Exception:
                            pass
                try:  # try to reopen the connection
                    con2 = con._create()
                except Exception:
                    pass
                else:
                    try:
                        cursor2 = con2.cursor(
                            *self._args, **self._kwargs)  # open new cursor
                    except Exception:
                        pass
                    else:
                        if transaction:
                            self.close()
                            con._close()
                            con._store(con2)
                            self._cursor = cursor2
                            raise error  # raise the original error again
                        error2 = None
                        try:  # try one more time to execute
                            if execute:
                                self._setsizes(cursor2)
                            method2 = getattr(cursor2, name)
                            result = method2(*args, **kwargs)
                            if execute:
                                self._clearsizes()
                        except error.__class__:  # same execution error
                            use2 = False
                            error2 = error
                        except Exception as error:  # other execution errors
                            use2 = True
                            error2 = error
                        else:
                            use2 = True
                        if use2:
                            self.close()
                            con._close()
                            con._store(con2)
                            self._cursor = cursor2
                            con._usage += 1
                            if error2:
                                raise error2  # raise the other error
                            return result
                        try:
                            cursor2.close()
                        except Exception:
                            pass
                    try:
                        con2.close()
                    except Exception:
                        pass
                if transaction:
                    self._transaction = False
                raise error  # re-raise the original error again
            else:
                con._usage += 1
                return result
        return tough_method

    def __getattr__(self, name):
        """Inherit methods and attributes of underlying cursor."""
        if self._cursor:
            if name.startswith(('execute', 'call')):
                # make execution methods "tough"
                return self._get_tough_method(name)
            else:
                return getattr(self._cursor, name)
        else:
            raise InvalidCursor

    def __del__(self):
        """Delete the steady cursor."""
        try:
            self.close()  # make sure the cursor is closed
        except Exception:
            pass
