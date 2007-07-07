"""
CodeGenerator.py


This module defines the basic machinery for a code generator, but cannot be used directly. Instead, use concrete generators like MySQLPythonGeneratory and MySQLSQLGenerator.

Terminology: "the standard classes" = ModelObject, Klasses, Klass and Attr

Modules that wish to do code generation must:
	* Define a class that inherits CodeGenerator (even if it's implementation is 'pass').
	* Define various mix-in classes such as ModelObject, Klasses, Klass and Attr for the purpose of defining methods to aid in code generation.

What happens: When the generator is initialized, mixes in the methods of various classes found in the module with the ones found in the model (typically these come from MiddleKit.Core).

TO DO
-----
Make sure all three goals are met:
	* User-defined classes can be used in place of the standard classes
	* Inheritance of generators is supported
	* Class inheritance (like Klasses inheriting ModelObject works)
"""


import os, sys

from MiscUtils.Configurable import Configurable
from time import asctime, localtime, time
from MiddleKit.Core.ModelUser import ModelUser

try: # for Python < 2.3
	True, False
except NameError:
	True, False = 1, 0


class CodeGenerator(ModelUser):

	def name(self):
		""" Returns the name of the generator for informational purposes. The name the is the class name. """
		return self.__class__.__name__

	def requireDir(self, dirname):
		if not os.path.exists(dirname):
			os.mkdir(dirname)
		assert os.path.isdir(dirname)

	def writeInfoFile(self, filename):
		file = open(filename, 'w')
		self.writeInfoItems(file)
		file.close()

	def writeInfoItems(self, file):
		wr = self.writeInfoItem
		wr(file, 'Date', asctime(localtime(time())))
		wr(file, 'Python ver', sys.version)
		wr(file, 'Op Sys', os.name)
		wr(file, 'Platform', sys.platform)
		wr(file, 'Cur dir', os.getcwd())

	def writeInfoItem(self, out, key, value):
		key = key.ljust(10)
		out.write('%s = %s\n' % (key, value))

	def generate(self, outdir):
		raise AbstractError, self.__class__
