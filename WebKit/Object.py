import os, sys

try:
	import MiscUtils
except ImportError:
	# When the Webware tarball unravels,
	# the components sit next to each other
	sys.path.append(os.path.abspath(os.pardir))
	import MiscUtils
from MiscUtils.NamedValueAccess import NamedValueAccess

try: # for Python < 2.2
	object
except NameError:
	class object: pass


class Object(object, NamedValueAccess):
	"""Object is the root class for all classes in the WebKit.

	This is a placeholder for any future functionality that might be
	appropriate for all objects in the framework.

	"""

	def __init__(self):
		"""Initializes the object. Subclasses should invoke super."""
		pass

	def deprecated(self, method):
		"""Output a deprecation warning.

		The implementation of WebKit sometimes invokes this method which prints
		a warning that the method you are using has been deprecated.
		This method expects that deprecated methods say so at the beginning of
		their doc string and terminate that msg with @. For example:

			DEPRECATED: Class.foo() on 01/24/01 in ver 0.5. Use Class.bar() instead. @

		Putting this information in the doc string is important for accuracy
		in the generated docs.

		Example call:
			self.deprecated(self.foo)

		"""
		docString = method.__doc__
		if docString:
			msg = docString.split('@')[0]
			msg = '\n'.join(map(lambda s: s.strip(), msg.splitlines()))
		else:
			msg = 'DEPRECATED: %s (no doc string)' % method
		print msg
		try:
			from traceback import format_stack
			print format_stack(limit =3)[0]
		except Exception:
			print 'Could not determine calling function.'

	# 2000-05-21 ce: Sometimes used for debugging:
	# def __del__(self): print '>> del', self
