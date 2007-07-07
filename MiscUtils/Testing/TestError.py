import types
import unittest

import sys
try:
	from MiscUtils.Error import Error
except:
	sys.path.insert(1, '..')
	from Error import Error

def test():
	err = Error(None, None)
	print 'str: ', err
	print 'repr:', repr(err)
	assert err.object() is None
	assert err.message() is None
	print

	err = Error(test, 'test')
	print 'str: ', err
	print 'repr:', repr(err)
	assert err.object() is test
	assert err.message() == 'test'
	print

	err = Error(None, '', a=5, b='.')
	check(err)

	err = Error(None, '', {'a': 5}, b='.')
	check(err)

def check(err):
	print 'str: ', err
	print 'repr:', repr(err)
	assert err.keys() in [['a', 'b'], ['b', 'a']]
	assert type(err['a']) is types.IntType
	assert type(err['b']) is types.StringType
	print


class TestError(unittest.TestCase):

	def testNone(self):
		err = Error(None, None)
		self.assertEqual('ERROR: None', str(err))
		self.assertEqual('ERROR(object=None; message=None; data={})', repr(err))

	def testObjMessage(self):
		err = Error(test, 'test')
		self.assertEqual('ERROR: test', str(err))
		# Should produce something like:
		# "ERROR(object=<function test at 0x74f70>; message='test'; data={})"
		self.assert_(repr(err).endswith("; message='test'; data={})"))

	def testValueDict(self):
		err = Error(None, '', a=5, b='.')
		self.assertEqual('ERROR: ', str(err))
		self.assertEqual("ERROR(object=None; message=''; data={'a': 5, 'b': '.'})",
			repr(err).replace("{'b': '.', 'a': 5}", "{'a': 5, 'b': '.'}"))
		assert err.keys() in [['a', 'b'], ['b', 'a']]
		assert type(err['a']) is types.IntType
		assert type(err['b']) is types.StringType

	def testVarArgs(self):
		err = Error(None, '', {'a': 5}, b='.')
		self.assertEqual('ERROR: ', str(err))
		self.assertEqual("ERROR(object=None; message=''; data={'a': 5, 'b': '.'})",
			repr(err).replace("{'b': '.', 'a': 5}", "{'a': 5, 'b': '.'}"))
		assert err.keys() in [['a', 'b'], ['b', 'a']]
		assert type(err['a']) is types.IntType
		assert type(err['b']) is types.StringType


if __name__ == '__main__':
	test()
