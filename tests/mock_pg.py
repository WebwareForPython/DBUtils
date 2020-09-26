"""This module serves as a mock object for the pg API module"""

import sys

sys.modules['pg'] = sys.modules[__name__]


class Error(Exception):
    pass


class DatabaseError(Error):
    pass


class InternalError(DatabaseError):
    pass


class ProgrammingError(DatabaseError):
    pass


def connect(*args, **kwargs):
    return pgConnection(*args, **kwargs)


class pgConnection:
    """The underlying pg API connection class."""

    def __init__(self, dbname=None, user=None):
        self.db = dbname
        self.user = user
        self.num_queries = 0
        self.session = []
        if dbname == 'error':
            self.status = False
            self.valid = False
            raise InternalError
        self.status = True
        self.valid = True

    def close(self):
        if not self.valid:
            raise InternalError
        self.num_queries = 0
        self.session = []
        self.status = False
        self.valid = False

    def reset(self):
        self.num_queries = 0
        self.session = []
        self.status = True
        self.valid = True

    def query(self, qstr):
        if not self.valid:
            raise InternalError
        if qstr in ('begin', 'end', 'commit', 'rollback'):
            self.session.append(qstr)
        elif qstr.startswith('select '):
            self.num_queries += 1
            return qstr[7:]
        elif qstr.startswith('set '):
            self.session.append(qstr[4:])
        else:
            raise ProgrammingError


class DB:
    """Wrapper class for the pg API connection class."""

    def __init__(self, *args, **kw):
        self.db = connect(*args, **kw)
        self.dbname = self.db.db
        self.__args = args, kw

    def __getattr__(self, name):
        if self.db:
            return getattr(self.db, name)
        else:
            raise AttributeError

    def close(self):
        if self.db:
            self.db.close()
            self.db = None
        else:
            raise InternalError

    def reopen(self):
        if self.db:
            self.close()
        try:
            self.db = connect(*self.__args[0], **self.__args[1])
        except Exception:
            self.db = None
            raise

    def query(self, qstr):
        if not self.db:
            raise InternalError
        return self.db.query(qstr)

    def get_tables(self):
        if not self.db:
            raise InternalError
        return 'test'
