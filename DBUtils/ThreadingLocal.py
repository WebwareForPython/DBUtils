"""Thread-local objects.

This module provides a Python version of the threading.local class.
It is avaliable as _threading_local in the standard library since Python 2.4.

Depending on the version of Python you're using, there may be a faster
threading.local class available in the standard library.

However, the C implementation turned out to be unusable with mod_wsgi,
since it does not keep the thread-local data between requests.
To have a reliable solution that works the same with all Python versions,
we fall back to this Python implemention in DBUtils.

"""

__all__ = ["local"]


try:
    from threading import current_thread
except ImportError: # Python >2.5
    from threading import currentThread as current_thread
from threading import RLock, enumerate


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
        current_thread().__dict__[key] = dict
        return self


def _patch(self):
    key = object.__getattribute__(self, '_local__key')
    d = current_thread().__dict__.get(key)
    if d is None:
        d = {}
        current_thread().__dict__[key] = d
        object.__setattr__(self, '__dict__', d)
        cls = type(self)
        if cls.__init__ is not object.__init__:
            args, kw = object.__getattribute__(self, '_local__args')
            cls.__init__(self, *args, **kw)
    else:
        object.__setattr__(self, '__dict__', d)


class local(_localbase):
    """A class that represents thread-local data."""

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

    def __del__(self):
        try:
            key = object.__getattribute__(self, '_local__key')
            threads = list(enumerate())
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
