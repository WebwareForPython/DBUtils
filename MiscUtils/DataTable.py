"""
DataTable.py


INTRODUCTION

This class is useful for representing a table of data arranged by named
columns, where each row in the table can be thought of as a record:

	name   phoneNumber
	------ -----------
	Chuck  893-3498
	Bill   893-0439
	John   893-5901

This data often comes from delimited text files which typically
have well defined columns or fields with several rows each of which can
be thought of as a record.

Using a DataTable can be as easy as using lists and dictionaries:

	table = DataTable('users.csv')
	for row in table:
		print row['name'], row['phoneNumber']

Or even:

	table = DataTable('users.csv')
	for row in table:
		print '%(name)s %(phoneNumber)s' % row

The above print statement relies on the fact that rows can be treated
like dictionaries, using the column headings as keys.

You can also treat a row like an array:

	table = DataTable('something.tabbed', delimiter='\t')
	for row in table:
		for item in row:
			print item,
		print


COLUMNS

Column headings can have a type specification like so:
	name, age:int, zip:int

Possible types include string, int, float and datetime. However,
datetime is not well supported right now.

String is assumed if no type is specified but you can set that
assumption when you create the table:

		table = DataTable(headings, defaultType='float')

Using types like int and float will cause DataTable to actually
convert the string values (perhaps read from a file) to these types
so that you can use them in natural operations. For example:

	if row['age']>120:
		self.flagData(row, 'age looks high')

As you can see, each row can be accessed as a dictionary with keys
according the column headings. Names are case sensitive.


ADDING ROWS

Like Python lists, data tables have an append() method. You can append
TableRecords, or you pass a dictionary, list or object, in which case a
TableRecord is created based on given values. See the method docs below
for more details.


FILES

By default, the files that DataTable reads from are expected to be
comma-separated value files.

Limited comments are supported: A comment is any line whose very first
character is a #. This allows you to easily comment out lines in your
data files without having to remove them.

Whitespace around field values is stripped.

You can control all this behavior through the arguments found in the
initializer and the various readFoo() methods:

	...delimiter=',', allowComments=True, stripWhite=True

For example:

	table = DataTable('foo.tabbed', delimiter='\t',
		allowComments=False, stripWhite=False)

You should access these parameters by their name since additional ones
could appear in the future, thereby changing the order.

If you are creating these text files, we recommend the
comma-separated-value format, or CSV. This format is better defined
than the tab delimited format, and can easily be edited and manipulated
by popular spreadsheets and databases.


MICROSOFT EXCEL

On Microsoft Windows systems with Excel and the win32all package
(http://starship.python.net/crew/mhammond/), DataTable will use Excel
(via COM) to read ".xls" files.

from MiscUtils import DataTable
assert DataTable.canReadExcel()
table = DataTable.DataTable('foo.xls')

With consistency to its CSV processing, DataTable will ignore any row
whose first cell is '#' and strip surrounding whitespace around strings.


TABLES FROM SCRATCH

Here's an example that constructs a table from scratch:

	table = DataTable(['name', 'age:int'])
	table.append(['John', 80])
	table.append({'name': 'John', 'age': 80})
	print table


QUERIES

A simple query mechanism is supported for equality of fields:

	matches = table.recordsEqualTo({'uid': 5})
	if matches:
		for match in matches:
			print match
	else:
		print 'No matches.'


COMMON USES

* Programs can keep configuration and other data in simple comma-
separated text files and use DataTable to access them. For example, a
web site could read it's sidebar links from such a file, thereby
allowing people who don't know Python (or even HTML) to edit these
links without having to understand other implementation parts of the
site.

* Servers can use DataTable to read and write log files.


FROM THE COMMAND LINE

The only purpose in invoking DataTable from the command line is to see
if it will read a file:

> python DataTable.py foo.csv

The data table is printed to stdout.


CACHING

DataTable uses "pickle caching" so that it can read .csv files faster
on subsequent loads. You can disable this across the board with:
	from MiscUtils.DataTable import DataTable
	DataTable._usePickleCache = False

Or per instance by passing "usePickleCache=False" to the constructor.

See the docstring of PickleCache.py for more information.


MORE DOCS

Some of the methods in this module have worthwhile doc strings to look
at. See below.


TO DO

* Allow callback parameter or setting for parsing CSV records.
* Perhaps TableRecord should inherit UserList and UserDict and override methods as appropriate...?
* Better support for datetime.
* _types and BlankValues aren't really packaged, advertised or
  documented for customization by the user of this module.
* DataTable:
	* Parameterize the TextColumn class.
	* Parameterize the TableRecord class.
	* More list-like methods such as insert()
	* writeFileNamed() is flawed: it doesn't write the table column
	  type
	* Should it inherit from UserList?
* Add error checking that a column name is not a number (which could
  cause problems).
* Look for various @@ tags through out the code.

"""


import os, sys
from types import *

from CSVParser import CSVParser
from CSVJoiner import joinCSVFields
from Funcs import positive_id
from MiscUtils import NoDefault, StringTypes, mxDateTime

try: # for Python < 2.3
	True, False
except NameError:
	True, False = 1, 0


## Types ##

DateTimeType = "<custom-type 'datetime'>"
ObjectType = "<type 'Object'>"

_types = {
	'string':   StringType,
	'int':      IntType,
	'bool':     IntType,
	'long':     LongType,
	'decimal':  FloatType,
	'float':    FloatType,
	'datetime': DateTimeType,
	'date':     DateTimeType,
	'object':   ObjectType
}


## Functions ##

def canReadExcel():
	try:
		from win32com.client import Dispatch
		Dispatch("Excel.Application")
	except:
		return False
	else:
		return True


## Classes ##


class DataTableError(Exception):
	pass


class TableColumn:
	"""Representation of a table column.

	A table column represents a column of the table including name and type.
	It does not contain the actual values of the column. These are stored
	individually in the rows.

	"""

	def __init__(self, spec):

		# spec is a string such as 'name' or 'name:type'
		fields = spec.split(':', 2)
		if len(fields) > 2:
			raise DataTableError, 'Invalid column spec %r' % spec
		self._name = fields[0]

		if len(fields) == 1:
			self._type = None
		else:
			self.setType(fields[1])

	def name(self):
		return self._name

	def type(self):
		return self._type

	def setType(self, type):
		"""Set the type (by a string containing the name) of the heading.

		Usually invoked by DataTable to set the default type for columns
		whose types were not specified.

		"""
		if type is None:
			self._type = None
		else:
			try:
				self._type = _types[type.lower()]
			except:
				raise DataTableError, 'Unknown type %r. types=%r' % (type, _types.keys())

	def __repr__(self):
		return '<%s %r with %r at %x>' % (
			self.__class__.__name__, self._name, self._type, positive_id(self))

	def __str__(self):
		return self._name


	## Utilities ##

	def valueForRawValue(self, rawValue):
		"""Set correct type for raw value.

		The rawValue is typically a string or value already of the appropriate
		type. TableRecord invokes this method to ensure that values (especially
		strings that come from files) are the correct types (e.g., ints are
		ints and floats are floats).

		"""
		# @@ 2000-07-23 ce: an if-else ladder?
		# perhaps these should be dispatched messages or a class hier
		if self._type is StringType:
			value = str(rawValue)
		elif self._type is IntType:
			if rawValue == '':
				value = 0
			else:
				value = int(rawValue)
		elif self._type is LongType:
			if rawValue == '':
				value = 0
			else:
				value = long(rawValue)
		elif self._type is FloatType:
			if rawValue == '':
				value = 0.0
			else:
				value = float(rawValue)
		elif self._type is DateTimeType:
			value = mxDateTime.DateTimeFrom(rawValue)
		elif self._type is ObjectType:
			value = rawValue
		else:
			# no type set, leave values as they are
			value = rawValue
		return value


class DataTable:
	"""Representation of a data table.

	See the doc string for this module.

	"""

	_usePickleCache = True


	## Init ##

	def __init__(self, filenameOrHeadings=None, delimiter=',',
			allowComments=True, stripWhite=True,
			defaultType=None, usePickleCache=None):
		if usePickleCache is None:
			self._usePickleCache = self._usePickleCache # grab class-level attr
		else:
			self._usePickleCache = usePickleCache
		if defaultType and not _types.has_key(defaultType):
			raise DataTableError, 'Unknown type for default type: %r' % defaultType
		self._defaultType = defaultType
		self._filename = None
		self._headings = []
		self._rows = []
		if filenameOrHeadings:
			if type(filenameOrHeadings) is StringType:
				self.readFileNamed(filenameOrHeadings, delimiter, allowComments, stripWhite)
			else:
				self.setHeadings(filenameOrHeadings)


	## File I/O ##

	def readFileNamed(self, filename, delimiter=',',
			allowComments=True, stripWhite=True, worksheet=1, row=1, column=1):
		self._filename = filename
		data = None
		if self._usePickleCache:
			from PickleCache import readPickleCache, writePickleCache
			data = readPickleCache(filename, pickleVersion=1, source='MiscUtils.DataTable')
		if data is None:
			if self._filename.lower().endswith('.xls'):
				self.readExcel(worksheet, row, column)
			else:
				file = open(self._filename, 'r')
				self.readFile(file, delimiter, allowComments, stripWhite)
				file.close()
			if self._usePickleCache:
				writePickleCache(self, filename, pickleVersion=1, source='MiscUtils.DataTable')
		else:
			self.__dict__ = data.__dict__
		return self

	def readFile(self, file, delimiter=',',
			allowComments=True, stripWhite=True):
		return self.readLines(file.readlines(), delimiter,
			allowComments, stripWhite)

	def readString(self, string, delimiter=',',
			allowComments=True, stripWhite=True):
		return self.readLines(string.split('\n'), delimiter,
			allowComments, stripWhite)

	def readLines(self, lines, delimiter=',',
			allowComments=True, stripWhite=True):
		if self._defaultType is None:
			self._defaultType = 'string'
		haveReadHeadings = False
		parse = CSVParser(fieldSep=delimiter, allowComments=allowComments,
			stripWhitespace=stripWhite).parse
		for line in lines:
			# process a row, either headings or data
			values = parse(line)
			if values:
				if haveReadHeadings:
					row = TableRecord(self, values)
					self._rows.append(row)
				else:
					self.setHeadings(values)
					haveReadHeadings = True
		if values is None:
			raise DataTableError, "Unfinished multiline record."
		return self

	def canReadExcel(self):
		return canReadExcel()

	def readExcel(self, worksheet=1, row=1, column=1):
		maxBlankRows = 10
		numRowsToReadPerCall = 20
		from win32com.client import Dispatch
		xl = Dispatch("Excel.Application")
		wb = xl.Workbooks.Open(os.path.abspath(self._filename))
		try:
			sh = wb.Worksheets(worksheet)
			sh.Cells(row, column)
			# determine max column
			numCols = 1
			while 1:
				if sh.Cells(row, numCols).Value in [None, '']:
					numCols -= 1
					break
				numCols += 1
			if numCols <= 0:
				return

			def strip(x):
				try:
					return x.strip()
				except:
					return x

			# read rows of data
			maxCol = chr(ord('A') + numCols - 1)
			haveReadHeadings = False
			rowNum = row
			numBlankRows = 0
			valuesBuffer = {} # keyed by row number
			while 1:
				try:
					# grab a single row
					values = valuesBuffer[rowNum]
				except KeyError:
					# woops. read buffer is out of fresh rows
					valuesRows = sh.Range('A%i:%s%i' % (rowNum, maxCol,
						rowNum+numRowsToReadPerCall-1)).Value
					valuesBuffer.clear()
					j = rowNum
					for valuesRow in valuesRows:
						valuesBuffer[j] = valuesRow
						j += 1
					values = valuesBuffer[rowNum]
				# non-"buffered" version, one row at a time:
				# values = sh.Range('A%i:%s%i' % (rowNum, maxCol,
				# rowNum)).Value[0]
				values = [strip(v) for v in values]
				nonEmpty = [v for v in values if v]
				if nonEmpty:
					if values[0] not in ('#', u'#'):
						if haveReadHeadings:
							row = TableRecord(self, values)
							self._rows.append(row)
						else:
							self.setHeadings(values)
							haveReadHeadings = True
					numBlankRows = 0
				else:
					numBlankRows += 1
					if numBlankRows > maxBlankRows:
						# consider end of spreadsheet
						break
				rowNum += 1
		finally:
			wb.Close()

	def save(self):
		self.writeFileNamed(self._filename)

	def writeFileNamed(self, filename):
		file = open(filename, 'w')
		self.writeFile(file)
		file.close()

	def writeFile(self, file):
		"""Write the table out as a file.

		@@ 2000-07-20 ce: This doesn't write the column types (like :int) back out.
		@@ 2000-07-21 ce: It's notable that a blank numeric value gets read as zero
			and written out that way. Also, values None are written as blanks.

		"""
		# write headings
		file.write(','.join(map(str, self._headings)))
		file.write('\n')

		def valueWritingMapper(item):
			# So that None gets written as a blank and everything else as a string
			if item is None:
				return ''
			else:
				return str(item)

		# write rows
		for row in self._rows:
			file.write(joinCSVFields(map(valueWritingMapper, row)))
			file.write('\n')

	def commit(self):
		if self._changed:
			self.save()
			self._changed = False


	## Headings ##

	def heading(self, index):
		if type(key) is StringType:
			key = self._nameToIndexMap[key]
		return self._headings[index]

	def hasHeading(self, name):
		return self._nameToIndexMap.has_key(name)

	def numHeadings(self):
		return len(self._headings)

	def headings(self):
		return self._headings

	def setHeadings(self, headings):
		"""Headings can be a list of strings (like ['name', 'age:int'])
		or a list of TableColumns or None. """
		if not headings:
			self._headings = []
		elif type(headings[0]) in StringTypes:
			self._headings = map(lambda h: TableColumn(h), headings)
		elif isinstance(headings[0], TableColumn):
			self._headings = list(headings)
		for heading in self._headings:
			if heading.type() is None:
				heading.setType(self._defaultType)
		self.createNameToIndexMap()


	## Row access (list like) ##

	def __len__(self):
		return len(self._rows)

	def __getitem__(self, index):
		return self._rows[index]

	def append(self, object):
		"""If object is not a TableRecord, then one is created,
		passing the object to initialize the TableRecord.
		Therefore, object can be a TableRecord, list, dictionary or object.
		See TableRecord for details.

		"""
		if not isinstance(object, TableRecord):
			object = TableRecord(self, object)
		self._rows.append(object)
		self._changed = True


	## Queries ##

	def recordsEqualTo(self, dict):
		records = []
		keys = dict.keys()
		for record in self._rows:
			matches = True
			for key in keys:
				if record[key] != dict[key]:
					matches = False
					break
			if matches:
				records.append(record)
		return records


	## As a string ##

	def __repr__(self):
		# Initial info
		s = ['DataTable: %s\n%d rows\n' % (self._filename, len(self._rows))]
		# Headings
		s.append('     ')
		s.append(', '.join(map(str, self._headings)))
		s.append('\n')
		# Records
		i = 0
		for row in self._rows:
			s.append('%3d. ' % i)
			s.append(', '.join(map(str, row)))
			s.append('\n')
			i += 1
		return ''.join(s)


	## As a dictionary ##

	def dictKeyedBy(self, key):
		"""Return a dictionary containing the contents of the table.

		The content is indexed by the particular key. This is useful
		for tables that have a column which represents a unique key
		(such as a name, serial number, etc.).

		"""
		dict = {}
		for row in self:
			dict[row[key]] = row
		return dict


	## Misc access ##

	def filename(self):
		return self._filename

	def nameToIndexMap(self):
		"""Speed-up index.

		Table rows keep a reference to this map in order to speed up
		index-by-names (as in row['name']).

		"""
		return self._nameToIndexMap


	## Self utilities ##

	def createNameToIndexMap(self):
		"""Create speed-up index.

		Invoked by self to create the nameToIndexMap after the table's
		headings have been read/initialized.

		"""
		map = {}
		for i in range(len(self._headings)):
			map[self._headings[i].name()] = i
		self._nameToIndexMap = map


# @@ 2000-07-20 ce: perhaps for each type we could specify a function
# to convert from string values to the values of the type.

BlankValues = {
	StringType:   '',
	IntType:      0,
	FloatType:    0.0,
	DateTimeType: '',
	None:         None,
}


class TableRecord:
	"""Representation of a table record."""


	## Init ##

	def __init__(self, table, values=None):
		"""Initialize table record.

		Dispatches control to one of the other init methods based on the type
		of values. Values can be one of three things:
			1. A TableRecord
			2. A list
			3. A dictionary
			4. Any object responding to hasValueForKey() and valueForKey().

		"""
		self._headings = table.headings()
		self._nameToIndexMap = table.nameToIndexMap()
		# @@ 2000-07-20 ce: Take out the headings arg to the init method
		# since we have an attribute for that

		if values is not None:
			valuesType = type(values)
			if valuesType is ListType  or  valuesType is TupleType:
				# @@ 2000-07-20 ce: check for required attributes instead
				self.initFromSequence(values)
			elif valuesType is DictType:
				self.initFromDict(values)
			elif valuesType is InstanceType:
				self.initFromObject(value)
			else:
				raise DataTableError, 'Unknown type for values %s.' % valuesType

	def initFromSequence(self, values):
		if len(self._headings) < len(values):
			raise DataTableError, ('There are more values than headings.\n'
				'headings(%d, %s)\nvalues(%d, %s)' % (len(self._headings),
				self._headings, len(values), values))
		self._values = []
		numHeadings = len(self._headings)
		numValues = len(values)
		assert numValues <= numHeadings
		for i in range(numHeadings):
			heading = self._headings[i]
			if i >= numValues:
				self._values.append(BlankValues[heading.type()])
			else:
				self._values.append(heading.valueForRawValue(values[i]))

	def initFromDict(self, dict):
		self._values = []
		for heading in self._headings:
			name = heading.name()
			if dict.has_key(name):
				self._values.append(heading.valueForRawValue(dict[name]))
			else:
				self._values.append(BlankValues[heading.type()])

	def initFromObject(self, object):
		"""Initialize from object.

		The object is expected to response to hasValueForKey(name) and
		valueForKey(name) for each of the headings in the table. It's
		alright if the object returns False for hasValueForKey(). In that
		case, a "blank" value is assumed (such as zero or an empty
		string). If hasValueForKey() returns True, then valueForKey() must
		return a value.

		"""
		self._values = []
		for heading in self._headings:
			name = heading.name()
			if object.hasValueForKey(name):
				self._values.append(heading.valueForRawValue(
					object.valueForKey(name)))
			else:
				self._values.append(BlankValues[heading.type()])


	## Accessing like a sequence or dictionary ##

	def __len__(self):
		return len(self._values)

	def __getitem__(self, key):
		if type(key) in StringTypes:
			key = self._nameToIndexMap[key]
		try:
			return self._values[key]
		except TypeError:
			raise TypeError, 'key=%r, key type=%r, self._values=%r' % (
				key, type(key), self._values)

	def __setitem__(self, key, value):
		if type(key) is StringType:
			key = self._nameToIndexMap[key]
		self._values[key] = value

	def __repr__(self):
		return '%s' % self._values

	def get(self, key, default=None):
		index = self._nameToIndexMap.get(key, None)
		if index is None:
			return default
		else:
			return self._values[index]

	def has_key(self, key):
		return self._nameToIndexMap.has_key(key)

	def keys(self):
		return self._nameToIndexMap.keys()

	def values(self):
		return self._values

	def items(self):
		items = []
		for key in self.keys():
			items.append((key, self[key]))
		return items


	## Additional access ##

	def asList(self):
		"""Return a sequence whose values are the same as the record's.

		The order of the sequence is the one defined by the table.

		"""
		# It just so happens that our implementation already has this
		return self._values[:]

	def asDict(self):
		"""Return a dictionary whose key-values match the table record."""
		dict = {}
		nameToIndexMap = self._nameToIndexMap
		for key in nameToIndexMap.keys():
			dict[key] = self._values[nameToIndexMap[key]]
		return dict


	## valueForFoo() family ##

	def valueForKey(self, key, default=NoDefault):
		if default is NoDefault:
			return self[key]
		else:
			return self.get(key, default)

	def valueForAttr(self, attr, default=NoDefault):
		return self.valueForKey(attr['Name'], default)


def main(args=None):
	if args is None:
		args = sys.argv
	for arg in args[1:]:
		dt = DataTable(arg)
		print '*** %s ***' % arg
		print dt
		print


if __name__ == '__main__':
	main()
