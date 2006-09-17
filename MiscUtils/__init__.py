# MiscUtils component
# Webware for Python
# See Docs/index.html

__all__ = ['Configurable', 'DBPool', 'DataTable', 'DictForArgs', 'Error', 'Funcs', 'MixIn', 'NamedValueAccess', 'PropertiesObject', 'unittest']


try:
	AbstractError  # Python might build this in some day.
except NameError:
	class AbstractError(NotImplementedError):
		"""
		This exception is raised by abstract methods in abstract classes. It
		is a special case of NotImplementedError, that indicates that the
		implementation won't ever be provided at that location in the future
		--instead the subclass should provide it.

		Typical usage:

			from MiscUtils import AbstractError

			class Foo:
				def bar(self):
					raise AbstractError, self.__class__

		Note that added the self.__class__ makes the resulting exception
		*much* more useful.
		"""
		pass

# @@ 2002-11-10 ce: SubclassResponsibilityError is deprecated in favor of AbstractError, post 0.7
SubclassResponsibilityError = AbstractError


class NoDefault:
	"""
	This provides a singleton "thing" which can be used to initialize
	the "default=" arguments for different retrieval methods. For
	example:

		from MiscUtils import NoDefault
		def bar(self, name, default=NoDefault):
			if default is NoDefault:
				return self._bars[name]  # will raise exception for invalid key
			else:
				return self._bars.get(name, default)

	The value None does not suffice for "default=" because it does not
	indicate whether or not a value was passed.

	Consistently using this singleton is valuable due to subclassing
	situations:

		def bar(self, name, default=NoDefault):
			if someCondition:
				return self.specialBar(name)
			else:
				return SuperClass.bar(name, default)

	It's also useful if one method that uses "default=NoDefault" relies
	on another object and method to which it must pass the default.
	(This is similar to the subclassing situation.)
	"""
	pass


def InstallInWebKit(appServer):
	pass
