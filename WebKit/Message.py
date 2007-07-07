"""Message

A very general (dumb) message class.

"""

from Common import *


class Message(Object):
	"""A very general message class.

	Message is the abstract, parent class for both Request and Response,
	and implements the behavior that is generic to both.

	Messages have:

		* A set of arguments.
		* A protocol.
		* A content type and length.

	FUTURE
		* Support for different types of encodings
	"""


	## Init ##

	def __init__(self):
		Object.__init__(self)
		self._args = {}


	## Content ##

	def contentLength(self):
		""" Returns the length of the message body or -1 if not known. """
		return -1

	def contentType(self):
		""" Returns the MIME type of the message body or None if not known. """
		return None


	## Protocol ##

	def protocol(self):
		"""Return the protocol-

		Returns the name and version of the protocol the message uses
		in the form protocol/majorVersion.minorVersion, for example, HTTP/1.1.

		"""
		# @@ 2000-04-09 ce: Move this down into HTTPSomething subclasses
		return 'HTTP/1.0'


	## Arguments ##

	# @@ 2000-05-10 ce: Are arguments really used for anything?

	def arg(self, name, default=NoDefault):
		if default is NoDefault:
			return self._args[name]
		else:
			return self._args.get(name, default)

	def setArg(self, name, value):
		self._args[name] = value

	def hasArg(self, name):
		return self._args.has_key(name)

	def deleteArg(self, name):
		del self._args[name]

	def clearArgs(self):
		self._args.clear()

	def argNames(self):
		""" Returns a list of argument names. """
		return self._args.keys()


	## Exception reports ##

	_exceptionReportAttrNames = ['args']

	def writeExceptionReport(self, handler):
		handler.writeTitle(self.__class__.__name__)
		handler.writeAttrs(self, self._exceptionReportAttrNames)
