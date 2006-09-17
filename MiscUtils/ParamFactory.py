from threading import Lock

class ParamFactory:
    def __init__(self, klass, **extraMethods):
        self.lock = Lock()
        self.cache = {}
        self.klass = klass
        for name, func in extraMethods.items():
            setattr(self, name, func)
    def __call__(self, *args):
        self.lock.acquire()
        if not self.cache.has_key(args):
            value = self.klass(*args)
            self.cache[args] = value
            self.lock.release()
            return value
        else:
            self.lock.release()
            return self.cache[args]
    def allInstances(self):
        return self.cache.values()
    
