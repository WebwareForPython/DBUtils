import sys


class ModelObject:


	## Debugging ##

	def printAttrs(self, out=None):
		if out is None:
			out = sys.stdout
		out.write('self = %s\n' % repr(self))
		out.write('self  attrs = %s\n' % self.__dict__.keys())
		out.write('class attrs = %s\n' % self.__class__.__dict__.keys())
