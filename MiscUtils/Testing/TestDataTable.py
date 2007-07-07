import unittest
import os
from glob import glob

#import FixPath
from MiscUtils import StringIO
from MiscUtils.DataTable import *


# @@ 2000-12-04 ce: We don't test the feature where record like objects,
# that respond to hasValueForKey() and valueForKey(), can be added to a table
# (as opposed to a sequence, dictionary or TableRecord instance).


class TestDataTable(unittest.TestCase):

	def xsetUp(self):
		# clear any cache files from pickle test
		for name in glob('*.cache'):
			print 'Removing', name
			os.remove(name)

	def _testSource(self, name, src, headings, data):
		# print name
		dt = DataTable()
		lines = src.split('\n')
		dt.readLines(lines)
		assert [col.name() for col in dt.headings()] == headings
		i = 0
		while i < len(dt):
			match = data[i]
			self.assertEquals(dt[i].asList(), match,
				'For element %d, I expected "%s" but got "%s"'
				% (i, match, dt[i].asList()))
			i += 1

	def test01_withPickle(self):
		DataTable.usePickleCache = 1
		self._test01()
		self._test01()

	def test01_noPickle(self):
		DataTable.usePickleCache = 0
		self._test01()

	def _test01(self):
		'''Simple tests...'''

		# Create table
		t = DataTable()

		# Headings 1
		t = DataTable()
		t.setHeadings([TableColumn('name'), TableColumn('age:int'),
			TableColumn('rating:float')])

		# Headings 2
		t = DataTable()
		t.setHeadings(['name', 'age:int', 'rating:float'])

		# Adding and accessing data
		a = ['John', '26', '7.2']
		b = ['Mary', 32, 8.3]
		t.append(a)
		t.append(b)
		assert t[-1].asList() == b
		assert t[-2].asDict() == {'name': 'John', 'age': 26, 'rating': 7.2}
		assert t[-1]['name'] == 'Mary'
		assert t[-2]['name'] == 'John'

		# Printing
		# print t

		# Writing file (CSV)
		answer = '''\
name,age,rating
John,26,7.2
Mary,32,8.3
'''
		out = StringIO()
		t.writeFile(out)
		results = out.getvalue()
		assert results == answer, '\n%r\n%r\n' % (results, answer)

		# Accessing rows
		for row in t:
			assert row['name'] == row[0]
			assert row['age'] == row[1]
			assert row['rating'] == row[2]
			for item in row:
				pass

		# Default type
		t = DataTable(defaultType='int')
		t.setHeadings(list('xyz'))
		t.append([1, 2, 3])
		t.append([4, 5, 6])
		assert t[0]['x'] - t[1]['z'] == -5

	def testBasics(self):
		# Basics
		src = '''\
"x","y,y",z
a,b,c
a,b,"c,d"
"a,b",c,d
"a","b","c"
"a",b,"c"
"a,b,c"
"","",""
"a","",
'''
		headings = ['x', 'y,y', 'z']
		data = [
			['a', 'b', 'c'],
			['a', 'b', 'c,d'],
			['a,b', 'c', 'd'],
			['a', 'b', 'c'],
			['a', 'b', 'c'],
			['a,b,c', '', ''],
			['', '', ''],
			['a', '', '']
		]
		self._testSource('Basics', src, headings, data)

		# Comments
		src = '''\
a:int,b:int
1,2
#3,4
5,6
'''
		headings = ['a', 'b']
		data = [
			[1, 2],
			[5, 6],
		]
		self._testSource('Comments', src, headings, data)

		# Multiline records
		src = '''\
a
"""Hi
there"""
'''
		headings = ['a']
		data = [
			['"Hi\nthere"'],
		]
		self._testSource('Multiline records', src, headings, data)

		# MiddleKit enums
		src = '''\
Class,Attribute,Type,Extras
#Foo,
,what,enum,"Enums=""foo, bar"""
,what,enum,"Enums='foo, bar'"
'''
		headings = 'Class,Attribute,Type,Extras'.split(',')
		data = [
			['', 'what', 'enum', 'Enums="foo, bar"'],
			['', 'what', 'enum', "Enums='foo, bar'"],
		]
		self._testSource('MK enums', src, headings, data)

		# Unfinished multiline record
		try:
			DataTable().readString('a\n"1\n')
		except DataTableError:
			pass  # just what we were expecting
		else:
			raise Exception, 'Failed to raise exception for unfinished multiline record'

	def testExcel_withPickle(self):
		DataTable.usePickleCache = 1
		self._testExcel()
		self._testExcel()

	def testExcel_noPickle(self):
		DataTable.usePickleCache = 0
		self._testExcel()

	def _testExcel(self):
		if canReadExcel():
			import sys
			sys.stderr = sys.stdout
			# print 'Testing Excel...'
			xlsfile = os.path.join(os.path.dirname(__file__), 'Sample3.xls')
			t = DataTable(xlsfile)
			assert t[0][0] == 1.0, t[0]
