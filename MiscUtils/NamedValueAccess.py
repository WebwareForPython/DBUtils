"""
NamedValueAccess provides functions, a mix-in class and a wrapper class
all for accessing Python objects by named attributes. You can use which
ever of the three approaches best suites your needs and style.


NOTES

If Python provided a root class 'Object' in the same tradition as other
OOP languages such as Smalltalk, Objective-C and Java, then we could
dispense with the global functions and simply stick with the mix-in.


TO DO

* The mix-in's valueForKey() could be out of slight alignment with the
  function, since they have different implementations. However, the test
  cases pass for both right now.

* Should the valueForKey() function provide for caching of bindings in
  the same manner than the mix-in does?
  If not, should the mix-in allow an option to *not* cache bindings?

* hasValueForKey() function? (We already have a method in the mix-in)

* valuesForNames() in the mix-in:
	* Change parameter 'keys' to 'names'
	* Use NoDefault instead of None in the parameters
	* Revisit doc string and test cases

* Testing: increase coverage

* Rename? class NamedValueAccess+ible:

* Benchmarking: Set this up in a new file:
	Testing/BenchNamedValueAccess.py
   so we can experiment with caching vs. not and other techniques.


PAST DESIGN DECISIONS

* Only if a name binds to a method is it invoked. Another approach is
  to invoke any value that is __call__able, but that is unPythonic: If
  obj.foo is a class or a function then obj.foo gives that class or
  function, not the result of invoking it. Method is the only
  convenience we provide, because that's one of the major points of
  providing this.


CREDIT

Chuck Esterbrook <echuck@mindspring.com>
Tavis Rudd <tavis@calrudd.com>

"""


import types
from MiscUtils import NoDefault


# if technique is zero, use bound methods in the _kvGetBindings cache, otherwise use unbound
# @@ 2000-05-31 ce: after additional testing we can probably scorge the technique=0 allowance
technique = 1


## Exceptions ##

class NamedValueAccessError(LookupError): pass
class ValueForKeyError(NamedValueAccessError): pass


class NamedValueAccess:
	"""Mix-in class for accessing Python objects by named attributes.

	This class is intended to be ancestor class such that you can say:
		from NamedValueAccess import *
		age = someObj.valueForName("age")
		name = someObj.valueForName("info.fields.name")

	This can be useful in setups where you wish to textually refer to the
	objects in a program, such as an HTML template processed in the context
	of an object-oriented framework.

	Keys can be matched to either methods or instance variables and with
	or without underscores.

	valueForName() can also traverse bona fide dictionaries (DictType).

	You can safely import * from this module.
	Only the NamedValueAccess class is exported.

	There is no __init__() method and never will be.

	You'll see the terms 'key' and 'name' in the class and its documentation.
	A 'key' is a single identifier such as 'foo'. A name could be key, or a
	qualified key, such as 'foo.bar.boo'. Names are generally more convenient
	and powerful, while key-oriented methods are more efficient and provide
	the atomic functionality that name-oriented methods are built upon.
	From a usage point of view, you normally just use the 'name' methods
	and forget about the 'key'.

	@@ 2000-05-21 ce: This class causes problems when used in WebKit for logging.
		Perhaps circular references?
		Involving self?
		Having to do with methods bound to their objects?

	@@ 2000-03-03 ce: document instance variables

	@@ 2000-04-24 ce: Some classes like UserDict need to use getitem()
	instead of getattr() and don't need to deal with _bindingForGetKey().

	@@ 2000-05-31 ce: Rename this class to NamedValues, NamedValueAccess, ValuesByName

	@@ This class probably needs to be in MiscUtils, as it's being used in that
	   way while MiddleKit was intended for "enterprise/business objects".

	"""


	## Accessing values by key ##

	def hasValueForKey(self, key):
		"""Check whether key is available.

		Returns true if the key is available, although that does not guarantee
		that there will not be errors caused by retrieving the key.

		"""
		return self._bindingForGetKey(key) is not None

	def valueForKey(self, key, default=NoDefault):
		"""Get value for given key.

		Suppose key is 'foo'.
		This method returns the value with the following precedence:
			1. Methods before non-methods
			2. Public attributes before private attributes

		More specifically, this method then returns one of the following:
			* self.foo()
			* self._foo()
			* self.foo
			* self._foo

		... or default, if it was specified,
		otherwise invokes and returns result of valueForUnknownKey().
		Note that valueForUnknownKey() normally returns an exception.

		See valueForName() which is a more advanced version of this method
		that allows multiple, qualified keys.

		"""
		binding = self._bindingForGetKey(key)

		if not binding:
			if default is NoDefault:
				return self.valueForUnknownKey(key, default)
			else:
				return default

		if type(binding) is types.MethodType:
			if technique:
				result = binding(self)
			else:
				result = binding()
			return result
		else:
			return getattr(self, binding)

	def hasValueForName(self, keysString):
		"""Check whether name is available."""
		try:
			value = self.valueForName(keysString)
		except NamedValueAccessError:
			return 0
		return 1

	def valueForName(self, keysString, default=None):
		"""Get the value for the given keysString.

		This is the more advanced version of valueForKey(), which can only
		handle single names. This method can handle
			'foo', 'foo1.foo2', 'a.b.c.d', etc.
		It will traverse dictionaries if needed.
		"""
		keys = keysString.split('.')
		return self.valueForKeySequence(keys, default)

	def valueForKeySequence(self, listOfKeys, default=None):
		"""Get the value for the given list of keys."""
		return _valueForKeySequence(self, listOfKeys, default)

	def valuesForNames(self, keys, default=None, defaults=None, forgive=0, includeNames=0):
		"""Get all values for given names.

		Returns a list of values that match the given keys, each of which is
		passed through valueForName() and so could be of the form 'a.b.c'.

		keys and defaults are sequences.
		default is any kind of object.
		forgive and includeNames are flags.

		If default is not None, then it is substituted when a key is not found.
		Otherwise, if defaults is not None, then it's corresponding/parallel
		value for the current key is substituted when a key is not found.
		Otherwise, if forgive is true, then unknown keys simply don't produce
		any values.
		Otherwise, if default and defaults are None, and forgive is false,
		then the unknown keys will probably raise an exception through
		self.valueForUnknownKey() although that method can always return
		a final, default value.
		if keys is None, then None is returned.
		If keys is an empty list, then None is returned.
		Often these last four arguments are specified by key.
		Examples:
			names = ['origin.x', 'origin.y', 'size.width', 'size.height']
			obj.valuesForNames(names)
			obj.valuesForNames(names, default=0.0)
			obj.valuesForNames(names, defaults=[0.0, 0.0, 100.0, 100.0])
			obj.valuesForNames(names, forgive=0)
		@@ 2000-03-04 ce: includeNames is only supported when forgive=1.
			It should be supported for the other cases.
			It should be documented.
			It should be included in the test cases.

		"""
		if keys is None:
			return None
		if len(keys) == 0:
			return []
		results = []

		if default is not None:
			results = map(lambda key, myself=self,
				mydefault=default: myself.valueForName(key, mydefault), keys)
		elif defaults is not None:
			if len(keys) is not len(defaults):
				raise NamedValueAccessError, \
					'Keys and defaults have mismatching lengths (%d and %d).' \
					% (len(keys), len(defaults))
			results = map(lambda key, default,
				myself=self: myself.valueForName(key, default), keys, defaults)
		elif forgive:
			results = []
			uniqueObject = 'uni' + 'que'
			for key in keys:
				value = self.valueForName(key, uniqueObject)
				if value is not uniqueObject:
					if includeNames:
						results.append((key, value))
					else:
						results.append(value)
		else:
			# no defaults, no forgiveness
			results = map(lambda key,
				myself=self: myself.valueForName(key), keys)
		return results

	def setValueForKey(self, key, value):
		"""Set value for a given key.

		Suppose key is 'foo'.
		This method sets the value with the following precedence:
			1. Public attributes before private attributes
			2. Methods before non-methods

		More specifically, this method then uses one of the following:
			@@ 2000-03-04 ce: fill in

		... or invokes handleUnknownSetKey().

		"""
		raise NotImplementedError # @@ 2000-03-04 ce

	def resetKeyBindings(self):
		"""Rest all key bindings, releasing alreaedy referenced values."""
		if hasattr(self, '_kvGetBindings'):
			self._kvGetBindings = {}


	## Errors ##

	def valueForUnknownKey(self, key, default):
		raise NamedValueAccessError, key

	def handleUnknownSetKey(self, key):
		raise NamedValueAccessError, key


	## Private ##

	def _bindingForGetKey(self, key):
		"""Get binding for given key.

		Bindings are cached. Bindings are methods or strings.

		"""

		# Make _kvGetBindings dictionary if we don't have one
		if not hasattr(self, '_kvGetBindings'):
			self._kvGetBindings = {}

		# Return the binding if we already have one
		if self._kvGetBindings.has_key(key):
			return self._kvGetBindings[key]

		# No binding, so we have to look for the key

		found = None  # set to what we find

		# Try plain old key
		if hasattr(self, key):
			found = getattr(self, key)
			if type(found) is not types.MethodType:
				found = key
			elif technique:
				found = getattr(self.__class__, key)
			self._kvGetBindings[key] = found

		# Try _key only if we didn't find a method called key
		if type(found) is not types.MethodType:
			underKey = '_' + key
			if hasattr(self, underKey):
				underAttr = getattr(self, underKey)
				if found is None:
					if type(underAttr) is types.MethodType:
						if technique:
							value = getattr(self.__class__, underKey)
						else:
							value = underAttr
					else:
						value = underKey
					found = self._kvGetBindings[key] = value
				else:
					if type(underAttr) is types.MethodType:
						if technique:
							underAttr = getattr(self.__class__, underKey)
						found = self._kvGetBindings[key] = underAttr

		return found


class NamedValueAccessWrapper(NamedValueAccess):
	"""Mix-in class for accessing Python objects by named attributes.

	This provides a wrapper around an existing object which will respond
	to the methods of NamedValueAccess. By using the wrapper, you can
	stick with objects and methods such as obj.valueForName('x.y') (as
	opposed to functions like valueForName()) and refrain from modifying
	the existing class hierarchy with NamedValueAccess.

	Example:
		wrapper = NamedValueAccessWrapper(obj)
		print wrapper.valueForName('manager.name')

	"""

	def __init__(self, object):
		self._object = object

	def hasValueForKey(self, key):
		try:
			value = self.valueForKey(ley)
		except NamedValueAccessError:
			return 0
		else:
			return 1

	def valueForKey(self, key, default=NoDefault):
		return valueForKey(self._object)

	def valueForName(self, key, default=NoDefault):
		return valueForName(self._object)


## Private ##

def _valueForKeySequence(obj, listOfKeys, default=None):
	"""Get the value of an object for a given list of keys.

	This is a recursive function used to implement
	NamedValueAccess.valueForKeySequence.
	Besides supporting inheritors of NamedValueAccess, this function also
	supports dictionaries, which is why it's not found in the class.

	"""

	# @@ 2000-02-18: Optimize by specifying index instead of making new list
	if type(obj) is types.DictType:
		try:
			value = obj[listOfKeys[0]]
		except: # @@ 2000-03-03 ce: this exception should be more specific. probably nameerror or indexerror
			if default is None:
				raise NamedValueAccessError, \
					'Unknown key (%s) in dictionary.' % listOfKeys[0]
			else:
				return default
	else:
		value = obj.valueForKey(listOfKeys[0], default)
	if len(listOfKeys) > 1:
		return _valueForKeySequence(value, listOfKeys[1:], default)
	else:
		return value


def _dict_valueForKey(obj, key, default=NoDefault):
	"""Get the value of a dict-like object for a given key.

	Returns the value for a given key of the dictionary-like object.
	This is a private, custom function built in support of valueForKey().

	"""
	try:
		value = obj[key]
	except AttributeError, e:
		# We attempt to pass only on exceptions caused
		# by obj not responding to __getitem__.
		# Any other exceptions generated get raised up.
		substring = "instance has no attribute '__getitem__'"
		if e.args[0][-len(substring):] == substring:
			if default is NoDefault:
				return None
			else:
				return
		else:
			raise
	except KeyError, e:
		if e.args[0] == key:
			if default is NoDefault:
				raise ValueForKeyError, key
			else:
				return default
		else:
			# If we get here, then the KeyError is deeper in the
			# implementation of obj[key]
			raise
	else:
		return value


def valueForKey(obj, key, default=NoDefault):
	"""Get the value of the object named by the given key.

	Suppose key is 'foo'.
	This method returns the value with the following precedence:
		1. Methods before non-methods
		2. Attributes before keys (__getitem__)
		3. Public things before private things
		   (private being denoted by a preceding underscore)

	More specifically, this method returns one of the following:
		* obj.valueForKey(key)  # only if the method exists
		* obj.foo()
		* obj._foo()
		* obj.foo
		* obj._foo
		* obj['foo']
		* obj.valueForUnknownKey(key)
		* default  # only if specified

	If all of these fail, a ValueForKeyError is raised.


	NOTES

	* If the object provides a valueForKey() method, that method will be
	  invoked to do the work.

	* valueForKey() works on dictionaries and dictionary-like objects.

	* valueForUnknownKey() provides a hook by which objects can
	  delegate or chain their keyed value access to other objects.
	  The key and default arguments are passed to it and it should
	  generally respect the typical treatment of the the default
	  argument as found throughout Webware and described in the Style
	  Guidelines.

	* See valueForName() which is a more advanced version of this
	  function that allows multiple, qualified keys.

	"""

	assert obj is not None

	# We only accept strings for keys
	assert type(key) is types.StringType

	# Use obj.valueForKey() if it is available
	valueForKeyMeth = getattr(obj, 'valueForKey', None)
	if valueForKeyMeth:
		return valueForKeyMeth(key, default)

	attr   = None
	method = None
	value  = None
	unknown = 0
	if type(obj) is types.DictType:
		if default is NoDefault:
			try:
				return obj[key]
			except KeyError:
				raise ValueForKeyError, key
		else:
			return obj.get(key, default)
	else:

		try:
			klass = obj.__class__
		except AttributeError:
			# happens for classes themselves
			klass = None
			method = None
		else:
			method   = getattr(klass, key, None)
		if not method:
			underKey = '_' + key
			method = klass and getattr(klass, underKey, None) or None
			if not method:
				attr = getattr(obj, key, NoDefault)
				if attr is NoDefault:
					attr = getattr(obj, underKey, NoDefault)
					if attr is NoDefault:
						if klass is not None:
							getitem = getattr(klass, '__getitem__', None)
							if getitem:
								try:
									value = getitem(obj, key)
								except KeyError:
									unknown = 1

#	if value is not NoDefault:
#		return value
	if not unknown:
		if method:
			return method(obj)
		if attr is not NoDefault:
			return attr

	# Use obj.valueForUnknownKey() if it is available
	valueForUnknownKey = getattr(obj, 'valueForUnknownKey', None)
	if valueForUnknownKey:
		return valueForUnknownKey(key, default)

	if default is not NoDefault:
		return default
	else:
		raise ValueForKeyError, key


def valueForName(obj, name, default=NoDefault):
	"""Get the value of the object that is named.

	The name can use dotted notation to traverse through a network/graph
	of objects. Since this function relies on valueForKey() for each
	individual component of the name, you should be familiar with the
	semantics of that notation.

	Example: valueForName(obj, 'department.manager.salary')

	"""
	names = name.split('.')
	for name in names:
		obj = valueForKey(obj, name, default)
		if obj is default:
			return obj
		# 2001-04-19 ce: I suppose the above technique could result in
		# the default being returned prematurely if it was part of the
		# chain of names. Well, that's just the way it goes for now.
	return obj


# Beef up UserDict with the NamedValueAccess base class and custom versions of
# hasValueForKey() and valueForKey(). This all means that UserDict's (such as
# os.environ) are key/value accessible.
# @@ 2000-05-07 ce: CGIWrapper.py duplicates this.
def _enhanceUserDict():
	from UserDict import UserDict
	if not NamedValueAccess in UserDict.__bases__:
		UserDict.__bases__ += (NamedValueAccess,)

		def _UserDict_hasValueForKey(self, key):
			return self.has_key(key)

		def _UserDict_valueForKey(self, key, default=NoDefault):
			if default is NoDefault:
				if self.has_key(key):
					return self[key]
				else:
					raise ValueForKeyError, key
			else:
				return self.get(key, default)

		setattr(UserDict, 'hasValueForKey', _UserDict_hasValueForKey)
		setattr(UserDict, 'valueForKey', _UserDict_valueForKey)

_enhanceUserDict()
