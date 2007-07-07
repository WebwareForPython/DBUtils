from PythonGenerator import Attr
from SQLPythonGenerator import SQLPythonGenerator
from MiscUtils import mxDateTime


class MSSQLPythonGenerator(SQLPythonGenerator):
	pass


class AnyDateTimeAttr:

	def _delme_writePySetChecks(self, out):
		Attr.writePySetChecks.im_func(self, out)
		if mxDateTime:
			out.write('''\
		# have DateTime
		if value is not None:
			if isinstance(value, type('')):
				value = DateTime.DateTimeFrom(value)
			if isinstance(value, DateTime.DateTimeDeltaType):
				# MS SQL Server has no such thing, only DateTime
				value = DateTime.DateTime(1900, 1, 1) + value
			if not isinstance(value, DateTime.%s):
				raise TypeError, 'expecting %s type, but got value %%r of type %%r instead' %% (value, type(value))
''' % (self.mxDateTimeTypeName(), self['Type']))
		else:
			out.write('''\
		# no DateTime, use strings
		if value is not None:
			if type(value) in StringTypes:
				raise TypeError, 'expecting string type, but got value %r of type %r instead' % (value, type(value))
''')
