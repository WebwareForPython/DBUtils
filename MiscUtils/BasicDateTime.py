"""Date and time classes.

Taken from http://www.pythonweb.org (Web Modules).

By default importing this module imports the Python > 2.3 datetime classes.
Otherwise the less powerful and robust lemon ones are used.

This module is really just meant to be the minimum date implementation that
can be got away with to enable lemon to work with Python < 2.3.

Documentation
-------------

See the Python 2.3 datetime module for documentation on the time, date and
datetime classes. WARNING: These versions do not properly check to make sure
the date you specified is valid.

now() returns the current date and time as a datetime object.

isodatetime2tuple(sql), isotime2tuple(sql) and isodate2tuple(sql) take a
standard isoformat string as would be returned from an sql query and return
the appropriate date or time object. WARNING: Parts of seconds are ignored.

calendar.weekday may break for certain old times. Not sure why, but that is
why it was all fixed in Python 2.3.

"""

import time as t
import calendar
from types import InstanceType

MINYEAR = 1
MAXYEAR = 9999


class DaysInMonth:
	"""Simple class to correctly calculate the days in a month in Python 2.2.

	The calendar.monthrange(year, month) fails in that version.

	"""

	def calculate(self, year, month):
		return (0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)[month] \
			+ (month == 2 and self.isleap(year))

	def isleap(self, year):
		"""Return 1 for leap years, 0 for non-leap years."""
		return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)

	def test(self):
		passed = 1
		for year in range (1, 9999):
			for month in range(1, 12):
				if DaysInMonth().calculate(year, month) != calendar.monthrange(year, month)[1]:
					print "Failed on %s-%s." % (year, month)
					passed = 0
		if not passed:
			print "FAILED"
		else:
			print "PASSED"
		return passed

	def weekday(self, year, month, day):
		"""Return weekday (0-6 ~ Mon-Sun) for year (1970-...), month (1-12), day (1-31)."""
		secs = mktime((year, month, day, 0, 0, 0, 0, 0, 0))
		tuple = localtime(secs)
		return tuple[6]

daysInMonth = DaysInMonth()


class datetime:
	"""DateTime(year, month=1, day=1, hour=0, minute=0, second=0.0)

	Constructs a DateTime instance from the given values.
	Assumes that the date is given in the Gregorian calendar
	(which it the one used in many countries today).

		WARNING:    Only very limited error checking is done for this class.
					The tuples are filled with the parameters from the last three numbers
					in the current time tuple so only use the first six!!

		Variable ranges:
			MINYEAR 1
			MAXYEAT 9999

			year    MINYEAR-MAXYEAR
			month   1-12
			day     1-31
			hour    0-23
			minute     0-59
			second     0-59  Apparantly it is possible to have a double leap second in Python.
							 However, to maintain compatibility with databases, this isn't allowed.

		WARNING:    Seconds are rounded to two decimal places.

	"""

	def __init__(self, year, month, day, hour=0, minute=0, second=0, microsecond=0):
		"""Initialize datetime object.

		All arguments are integers except second which can be a float.

			WARNING:	Possible problems with months with more days in than they actually have.

		"""

		dates = ('year', 'month', 'day', 'hour', 'minute')
		counter = 0
		for item in (year, month, day, hour, minute):
			if type(item) not in (type(1), type(1L)):
				raise TypeError("The variable '%s' should be an integer."
					% dates[counter])
			counter += 1

		if type(second) not in (type(1), type(1L)): # and type(second) != type(1.1)
			raise ValueError("The variable 'second' should be an Integer or a Long.") # or a float

		# Very basic error checking and initialisation.
		if not MINYEAR <= year <= MAXYEAR:
			raise ValueError('The year value must be between %s and %s inclusive.'
				% (MINYEAR, MAXYEAR))
		else:
			self.year = year
		if not 1 <= month < 1 <= 12:
			raise ValueError('The month value must be between 1 and 12 inclusive.')
		else:
			self.month = month
		if not 1 <= day <= daysInMonth.calculate(year, month):
			raise ValueError('The day value must be between 1 and %s inclusive.'
				% daysInMonth.calculate(year, month))
		else:
			self.day = day
		if not 0 <= hour < 24:
			raise ValueError('The hour value must be between 0 and 23 inclusive.')
		else:
			self.hour = hour
		if not 0 <= minute < 60:
			raise ValueError('The minutes value must be between 0 and 59 inclusive.')
		else:
			self.minute = minute
		if not 0 <= second < 60:
			raise ValueError('The seconds value must be between 0 and 59 inclusive.')
		else:
			self.second = second
		if not 0 <= microsecond < 1000000:
			raise ValueError('The microseconds value must be between 0 and 999999 inclusive.')
		else:
			self.microsecond = microsecond

	def now(self):
		"""Return the current date and time as a datetime."""
		now = t.localtime()
		return datetime(now[0], now[1], now[2], now[3], now[4], now[5])


	## Comparison Operators ##

	def _compareDate(self, other):
		if self.year == other.year:
			if self.month == other.month:
				if self.day == other.day:
					return 0
				elif self.day > other.day:
					return 1
				else:
					return -1
			elif self.month > other.month:
				return 1
			else:
				return -1
		elif self.year > other.year:
			return 1
		else:
			return -1

	def _compareTime(self, other):
		if self.hour == other.hour:
			if self.minute == other.minute:
				if self.second == other.second:
					return 0
				elif self.second > other.second:
					return 1
				else:
					return -1
			elif self.minute > other.minute:
				return 1
			else:
				return -1
		elif self.hour > other.hour:
			return 1
		else:
			return -1

	def __cmp__(self, other):
		if type(other) is type(None):
			raise Exception('This comparison is not supported')
		elif type(other) is InstanceType:
			if other.__class__.__name__ == self.__class__.__name__:
				if other.__class__.__name__ == 'date':
					return self._compareDate(other)
				elif other.__class__.__name__ == 'time':
					return self._compareTime(other)
				elif other.__class__.__name__ == 'datetime':
					date = self._compareDate(other)
					if date == 0:
						return self._compareTime(other)
					else:
						return date
				else:
					raise Exception('This comparison is not supported')
			else:
				raise Exception('This comparison is not supported')
		else:
			raise Exception('This comparison is not supported')

	def __eq__(self, other):
		if type(other) is InstanceType:
			if other.__class__.__name__ == self.__class__.__name__:
				if other.__class__.__name__ == 'date':
					if self._compareDate(other) == 0:
						return 1
					else:
						return 0
				elif other.__class__.__name__ == 'time':
					if self._compareTime(other) == 0:
						return 1
					else:
						return 0
				elif other.__class__.__name__ == 'datetime':
					date = self._compareDate(other)
					if date == 0:
						if self._compareTime(other) == 0:
							return 1
						else:
							return 0
					else:
						return 0
				else:
					return 0
			else:
				return 0
		else:
			return 0

	def __ne__(self, other):
		if self.__eq__(other):
			return 0
		else:
			return 1

	def __str__(self):
		"""Return the object as standard SQL."""
		return self.isoformat()

	def __repr__(self):
		"""Return a string representation of the object."""
		return "datetime.datetime(%s, %s, %s, %s, %s, %s)" % (
			self.year, self.month, self.day, self.hour, self.minute, self.second)

	def __getitem__(self, item):
		"""Enable dictionary-style attribute reading for year, month, day, hour, minute and second."""
		if item == 'year':
			return self.year
		elif item == 'month':
			return self.month
		elif item == 'day':
			return self.day
		elif item == 'hour':
			return self.hour
		elif item == 'minute':
			return self.minute
		elif item == 'second':
			return self.second
		else:
			raise KeyError("'%s' is not a valid attribute for a Date class." % item)


	## Formatting ##

	def _addZeros(self, num, s):
		"""Private function to add an appropriate number of zeros to s such that len(s) is num."""
		s = str(s)
		while len(s) < num:
			s = '0' + s
		return s

	def _isodate(self):
		"""Return the date as a standard SQL string of the format 'YYYY-MM-DD'."""
		return (str(self._addZeros(4, self.year))
			+ "-" + str(self._addZeros(2, self.month))
			+ "-" + str(self._addZeros(2, self.day)))

	def _isotime(self):
		"""Return the time as a standard SQL string in the format 'HH:MM::SS.ss'."""
		return (str(self._addZeros(2, self.hour))
			+ ":" + str(self._addZeros(2, self.minute))
			+ ":" + str(self._addZeros(2, self.second)))

	def strftime(self, format):
		"""Format the time using standard time module string format strings.

			%a Locale's abbreviated weekday name.
			%A Locale's full weekday name.
			%b Locale's abbreviated month name.
			%B Locale's full month name.
			%c Locale's appropriate date and time representation.
			%d Day of the month as a decimal number [01, 31].
			%H Hour (24-hour clock) as a decimal number [00, 23].
			%I Hour (12-hour clock) as a decimal number [01, 12].
			%j Day of the year as a decimal number [001, 366].
			%m Month as a decimal number [01, 12].
			%M Minute as a decimal number [00, 59].
			%p Locale's equivalent of either AM or PM.
			%S Second as a decimal number [00, 61]. (1)
			%U Week number of the year (Sunday as the first day of the week)
				as a decimal number [00, 53]. All days in a new year preceding
				the first Sunday are considered to be in week 0.
			%w Weekday as a decimal number [0(Sunday), 6].
			%W Week number of the year (Monday as the first day of the week)
				as a decimal number [00, 53]. All days in a new year preceding
				the first Monday are considered to be in week 0.
			%x Locale's appropriate date representation.
			%X Locale's appropriate time representation.
			%y Year without century as a decimal number [00, 99].
			%Y Year with century as a decimal number.
			%Z Time zone name (no characters if no time zone exists).
			%% A literal "%" character.
		"""
		return t.strftime(format, self.timetuple())


	## Conversion ##

	def timetuple(self):
		"""Return the date and time as a python tuple as constructed by time.localtime().

		WARNING: The last 3 entries in the tuple are obtained from time.localtime()
		and do not represent anything.

		"""
		sql =  self.isoformat()
		wday = calendar.weekday(int(sql[0:4]), int(sql[5:7]), int(sql[8:10]))
		return (int(sql[0:4]), int(sql[5:7]), int(sql[8:10]), int(sql[11:13]),
			int(sql[14:16]), int(sql[17:19]), wday, 0, -1)

	def isoformat(self):
		"""Return the date and time as a standard SQL string of the format 'YYYY-MM-DD HH:MM:SS.ss'."""
		return self._isodate() + ' ' + self._isotime()


class date(datetime):
	"""Constructs an object holding a date value.

	Is just another name binding for DateTime().
	The time part is set to '00:00:00.00'.

	"""

	def __init__(self, year, month, day):

		dates = ('year', 'month', 'day')
		counter = 0
		for item in (year, month, day):
			if type(item) not in (type(1), type(1L)):
				raise TypeError("The variable '%s' should be an Integer or a Long."
					% dates[counter])
			counter += 1

		# Very basic error checking and initialisation.
		if not MINYEAR <= year <= MAXYEAR:
			raise ValueError('The year value must be between %s and %s inclusive.'
				% (MINYEAR, MAXYEAR))
		else:
			self.year = year
		if not 1 <= month < 12:
			raise ValueError('The month value must be between 1 and 12 inclusive.')
		else:
			self.month = month
		if not 1 <= day <= daysInMonth.calculate(year, month):
			raise ValueError('The day value must be between 1 and %s inclusive.'
				% daysInMonth.calculate(year, month))
		else:
			self.day = day

	def __repr__(self):
		"""Return a string representation of the object."""
		return "datetime.date(%s, %s, %s)" % (self.year, self.month, self.day)

	def isoformat(self):
		"""Return the date as a standard SQL string of the format 'YYYY-MM-DD'."""
		return self._isodate()

	def timetuple(self):
		"""Returns the date as a python tuple as constructed by time.localtime().

		WARNING: The last 6 entries in the tuple are obtained from time.localtime()
		and do not represent anything.

		"""
		sql = self.isoformat()
		wday = calendar.weekday(int(sql[0:4]), int(sql[5:7]), int(sql[8:10]))
		return (int(sql[0:4]), int(sql[5:7]), int(sql[8:10]), 0, 0, 0, wday, 0, -1)

	def now(self):
		"""Return the current date and time as a datetime."""
		now = t.localtime()
		return date(now[0], now[1], now[2])


class time(datetime):
	"""Construct an object holding a time value.

	Is just another name binding for DateTime().
	The date part is set to '2000-01-01'.

	"""

	def __init__(self, hour=0, minute=0, second=0, microsecond=0):

		dates = ('hour', 'minute')
		counter = 0
		for item in (hour, minute):
			if type(item) not in (type(1), type(1L)):
				raise TypeError("The variable '%s' should be an Integer or a Long."
					% dates[counter])
			counter += 1

		if type(second) != type(1): # and type(second) != type(1.1):
			raise ValueError("The variable 'second' should be an integer.") # or a float

		# Very basic error checking and initialisation.

		if not 0 <= hour < 24:
			raise ValueError('The hour value must be between 0 and 23 inclusive.')
		else:
			self.hour = hour
		if not 0 <= minute < 60:
			raise ValueError('The minutes value must be between 0 and 59 inclusive.')
		else:
			self.minute = minute
		if not 0 <= second < 60:
			raise ValueError('The seconds value must be between 0 and 59 inclusive.')
		else:
			self.second = second
		if not 0 <= microsecond < 1000000:
			raise ValueError('The microseconds value must be between 0 and 999999 inclusive.')
		else:
			self.microsecond = microsecond

	def __repr__(self):
		"""Return a string representation of the object."""
		return "datetime.time(%s, %s, %s)" % (self.hour, self.minute, self.second)

	def isoformat(self):
		"""Return the time as a standard SQL string in the format 'HH:MM::SS.ss'."""
		return self._isotime()

	def timetuple(self):
		raise AttributeError('time objects do not have a timetuple method.')

	def now(self):
		"""Return the current date and time as a datetime."""
		now = t.localtime()
		return time(now[3], now[4], now[5])
