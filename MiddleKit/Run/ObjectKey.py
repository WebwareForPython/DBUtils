
class ObjectKey:
	"""
	An ObjectKey is used by ObjectStore for keeping track of objects in memory.

	Currently a key is equal to the class name of the object combined with the object's serial number, although as a user of object keys, you don't normally need to know what's inside them.
	"""


	def __init__(self):
		pass

	def initFromObject(self, object):
		""" Initializes the key and potentially invokes object.setSerialNum() if the object does not have one. The key does not maintain a reference to either the object or the store. """
		self._className = object.__class__.__name__
		self._serialNum = object.serialNum()
		if self._serialNum is 0:
			self._serialNum = object.store().newSerialNum()
			object.setSerialNum(self._serialNum)
		return self

	def initFromClassNameAndSerialNum(self, className, serialNum):
		assert className is not None
		assert serialNum > 0
		self._className = className
		self._serialNum = serialNum
		return self

	def serialNum(self):
		return self._serialNum

	def __cmp__(self, other):
		result = cmp(self._className, other._className)
		if result is 0:
			result = cmp(self._serialNum, other._serialNum)
		return result

	def __hash__(self):
		return hash(self._className) ^ hash(self._serialNum)

	def __str__(self):
		return '<%s, %s>' % (self._className, self._serialNum)
