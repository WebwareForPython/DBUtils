from Common import *
from Message import Message


class Response(Message):
	"""The abstract response class.

	Response is a type of Message that offers the following:

		* @@ 2000-04-17 ce
		* ...

	Response is an abstract class; developers typically use HTTPResponse.

	FUTURE
		* Consider implementing the buffer/flush logic here
		  including buffer size.
		* Also, consider then having a method that doesn't allow
		  committment until the end.

	"""


	## Init ##

	def __init__(self, trans, strmOut):
		Message.__init__(self)
		self._strmOut = strmOut
		self._transaction = trans


	## End time ##

	def endTime(self):
		return self._endTime

	def recordEndTime(self):
		"""Record the end time of the response.

		Stores the current time as the end time of the response. This should
		be invoked at the end of deliver(). It may also be invoked by the
		application for those responses that never deliver due to an error.

		"""
		self._endTime = time.time()


	## Output ##

	def write(self, string):
		raise AbstractError, self.__class__

	def isCommitted(self):
		raise AbstractError, self.__class__

	def deliver(self):
		raise AbstractError, self.__class__

	def reset(self):
		raise AbstractError, self.__class__

	def streamOut(self):
		return self._strmOut


	## Cleanup ##

	def clearTransaction(self):
		del self._transaction


	## Exception reporting ##

	_exceptionReportAttrNames = Message._exceptionReportAttrNames + ['endTime']
