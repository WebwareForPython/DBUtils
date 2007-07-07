from UserDict import UserDict


class Error(UserDict):
	"""
	An error is a dictionary-like object, containing a specific user-readable error message and an object associated with it. Since Error inherits UserDict, other informative values can be arbitrarily attached to errors. For this reason, subclassing Error is rare.

	Example:
		err = Error(user, 'Invalid password.')
		err['time'] = time.time()
		err['attempts'] = attempts

	The object and message can be accessed via methods:
		print err.object()
		print err.message()

	When creating errors, you can pass None for both the object and the message. You can also pass additional values, which are then included in the error:
		>>> err = Error(None, 'Too bad.', timestamp=time.time())
		>>> err.keys()
		['timestamp']

	Or include the values as a dictionary, instead of keyword arguments:
		>>> info = {'timestamp': time.time()}
		>>> err = Error(None, 'Too bad.', info)

	Or you could even do both if you needed to.
	"""

	def __init__(self, object, message, valueDict={}, **valueArgs):
		""" Initializes an error with the object the error occurred for, and the user-readable error message. The message should be self sufficient such that if printed by itself, the user would understand it. """
		UserDict.__init__(self)
		self._object    = object
		self._message   = message
		self.update(valueDict)
		self.update(valueArgs)

	def object(self):
		return self._object

	def message(self):
		return self._message

	def __repr__(self):
		return 'ERROR(object=%s; message=%s; data=%s)' % (repr(self._object), repr(self._message), repr(self.data))

	def __str__(self):
		return 'ERROR: %s' % self._message

	def __nonzero__(self):
		return 1
