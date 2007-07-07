import sys, unittest
from MiscUtils.DictForArgs import *


class TestDictForArgs(unittest.TestCase):

	def testPositives(self):
#		print 'Positive cases:'
		tests = '''\
# Basics
x=1       == {'x': '1'}
x=1 y=2   == {'x': '1', 'y': '2'}

# Strings
x='a'     == {'x': 'a'}
x="a"     == {'x': 'a'}
x='a b'   == {'x': 'a b'}
x="a b"   == {'x': 'a b'}
x='a"'    == {'x': 'a"'}
x="a'"    == {'x': "a'"}
x="'a'"   == {'x': "'a'"}
x='"a"'   == {'x': '"a"'}

# No value
x         == {'x': '1'}
x y       == {'x': '1', 'y': '1'}
x y=2     == {'x': '1', 'y': '2'}
x=2 y     == {'x': '2', 'y': '1'}
'''
		tests = string.split(tests, '\n')
		errCount = 0
		self._testPositive('', {})
		self._testPositive(' ', {})
		for test in tests:
			if '#' in test:
				test = test[:string.index(test, '#')]
			test = string.strip(test)
			if test:
				input, output = string.split(test, '==')
				output = eval(output)

				result = DictForArgs(input)

				self._testPositive(input, output)

	def _testPositive(self, input, output):
# 		print repr(input)
# 		sys.stdout.flush()
		result = DictForArgs(input)

		self.assertEquals(result, output,
			'Expecting: %s\nGot: %s\n' % (repr(output), repr(result)))

	def testNegatives(self):
#		print 'Negative cases:'
		cases = '''\
-
$
!@#$
'x'=5
x=5 'y'=6
'''
		cases = string.split(cases, '\n')
		errCount = 0
		for case in cases:
			if '#' in case:
				case = case[:string.index(case, '#')]
			case = string.strip(case)
			if case:
				self._testNegative(case)

	def _testNegative(self, input):
#		print repr(input)
#		sys.stdout.flush()
		try:
			result = DictForArgs(input)
		except DictForArgsError:
			return # success
		except:
			self.fail('Expecting DictForArgError.\nGot: %s.\n' % sys.exc_info())
		else:
			self.fail('Expecting DictForArgError.\nGot: %s.\n' % repr(result))

	def testPyDictForArgs(self):
		cases = '''\
		x=1 == {'x': 1}
		x=1; y=2 == {'x': 1, 'y': 2}
		x='a' == {'x': 'a'}
		x="a"; y="""b""" == {'x': 'a', 'y': 'b'}
		x=(1, 2, 3) == {'x': (1, 2, 3)}
		x=['a', 'b'] == {'x': ['a', 'b']}
		x='a b'.split() == {'x': ['a', 'b']}
		x=['a b'.split(), 1]; y={'a': 1} == {'x': [['a', 'b'], 1], 'y': {'a': 1}}
'''.split('\n')
		for case in cases:
			case = case.strip()
			if case:
				source, answer = case.split('==')
				answer = eval(answer)
				assert PyDictForArgs(source) == answer
