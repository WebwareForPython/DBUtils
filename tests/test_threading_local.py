"""Test the ThreadingLocal module."""

from threading import Thread

from dbutils.persistent_db import local


def test_getattr():
    my_data = local()
    my_data.number = 42
    assert my_data.number == 42


def test_dict():
    my_data = local()
    my_data.number = 42
    assert my_data.__dict__ == {'number': 42}
    my_data.__dict__.setdefault('widgets', [])
    assert my_data.widgets == []


def test_threadlocal():
    def f():
        items = sorted(my_data.__dict__.items())
        log.append(items)
        my_data.number = 11
        log.append(my_data.number)
    my_data = local()
    my_data.number = 42
    log = []
    thread = Thread(target=f)
    thread.start()
    thread.join()
    assert log == [[], 11]
    assert my_data.number == 42


def test_subclass():

    class MyLocal(local):
        number = 2
        initialized = 0

        def __init__(self, **kw):
            if self.initialized:
                raise SystemError
            self.initialized = 1
            self.__dict__.update(kw)

        def squared(self):
            return self.number ** 2

    my_data = MyLocal(color='red')
    assert my_data.number == 2
    assert my_data.color == 'red'
    del my_data.color
    assert my_data.squared() == 4

    def f():
        items = sorted(my_data.__dict__.items())
        log.append(items)
        my_data.number = 7
        log.append(my_data.number)

    log = []
    thread = Thread(target=f)
    thread.start()
    thread.join()
    assert log == [[('color', 'red'), ('initialized', 1)], 7]
    assert my_data.number == 2
    assert not hasattr(my_data, 'color')

    class MyLocal(local):
        __slots__ = ('number',)

    my_data = MyLocal()
    my_data.number = 42
    my_data.color = 'red'
    thread = Thread(target=f)
    thread.start()
    thread.join()
    assert my_data.number == 7
