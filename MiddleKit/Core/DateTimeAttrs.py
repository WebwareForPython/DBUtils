from Attr import Attr


class AnyDateTimeAttr(Attr):

	def __init__(self, dict):
		Attr.__init__(self, dict)


class DateTimeAttr(AnyDateTimeAttr):

	def __init__(self, dict):
		Attr.__init__(self, dict)


class DateAttr(AnyDateTimeAttr):

	def __init__(self, dict):
		Attr.__init__(self, dict)


class TimeAttr(AnyDateTimeAttr):

	def __init__(self, dict):
		Attr.__init__(self, dict)

# @@ 2000-10-13 ce: complete
