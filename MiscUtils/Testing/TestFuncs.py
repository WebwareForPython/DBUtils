import unittest
import sys
import string

try:
	from MiscUtils.Funcs import *
except:
	sys.path.insert(1, '..')
	from Funcs import *

# Used in testSafeDescription() below.
class Foo:
	pass

class TestFuncs( unittest.TestCase ):


	def testCommas(self):
		testSpec = '''
			0 '0'
			0.0 '0.0'
			1 '1'
			11 '11'
			111 '111'
			1111 '1,111'
			11111 '11,111'
			1.0 '1.0'
			11.0 '11.0'
			1.15 '1.15'
			12345.127 '12,345.127'
			-1 '-1'
			-11 '-11'
			-111 '-111'
			-1111 '-1,111'
			-11111 '-11,111'
		'''
		tests = string.split(testSpec)
		count = len(tests)
		i = 0
		while i < count:
			source = eval(tests[i])
			result = eval(tests[i+1])
			#print '%r yields %r' % (source, result)
			assert commas(source) == result, \
				'%r %r' % (commas(source), result)

			# Now try the source as a string instead of a number:
			source = eval("'%s'" % tests[i])
			#print '%r yields %r' % (source, result)
			assert commas(source)==result, \
				'%r %r' % (commas(source), result)

			i += 2


	def testLocalIP(self):
		ip = localIP()
		assert localIP() == ip  # second invocation
		assert localIP(useCache=None) == ip
		assert localIP(remote=None, useCache=None) == ip, \
			'See if this works: localIP(remote=None). If this fails, dont worry.'
		assert localIP(remote=('www.aslkdjsfliasdfoivnoiedndfgncvb.com', 80), useCache=None) == ip


	def testHostName(self):
		# About all we can do is invoke hostName() to see that no
		# exceptions are thrown, and do a little type checking on the
		# return type.
		host = hostName()
		assert host is None  or  type(host) is type(''), \
			'host type = %s, host = %s' % (type(host), repr(host))


	def testSafeDescription(self):
		sd = safeDescription

		# basics:
		s = sd(1).replace('type=', 'class=')
		assert s == "what=1 class=<type 'int'>", s
		s = sd(1, 'x').replace('type=', 'class=')
		assert s == "x=1 class=<type 'int'>", s
		s = sd('x').replace('type=', 'class=')
		s = s.replace("<type 'string'>", "<type 'str'>")
		assert s == "what='x' class=<type 'str'>", s
		f = Foo()
		assert sd(f).find('TestFuncs.Foo') != -1, sd(f)

		# new object type:
		try:
			object  # more recent versions of Python have a builtin object type
		except NameError:
			pass  # must be old Python
		else:
			class Bar(object): pass
			b = Bar()
			assert sd(b).find('TestFuncs.Bar') != -1, sd(b)

		# okay now test that safeDescription eats exceptions from repr():
		class Baz:
			def __repr__(self):
				raise KeyError, 'bogus'
		b = Baz()
		try:
			s = sd(b)
			s = s.replace("'bogus'", 'bogus') # new style
			s = s.replace("<class 'exceptions.KeyError'>", # new style
				'exceptions.KeyError')
			s = s.replace("<type 'exceptions.KeyError'>", # even newer style
				'exceptions.KeyError')
		except:
			s = 'failure: should not get exception'
		assert s.find("(exception from repr(x): exceptions.KeyError: bogus)") != -1, s


	def testUniqueId(self):
		lastResult = None
		for x in range(5):
			result = uniqueId()
			assert type(result) is type('')
			assert len(result) == 32
			assert result != lastResult

			result = uniqueId(self.testUniqueId)
			assert type(result) is type('')
			assert len(result) == 32
			assert result != lastResult


	def testValueForString(self):
		evalCases = '''
			1
			5L
			5.5
			True
			False
			None
			[1]
			['a']
			{'x':1}
			(1, 2, 3)
			'a'
			"z"
			"""1234"""
		'''

		stringCases = '''
			kjasdfkasdf
			2389234lkdsflkjsdf
			*09809
		'''

		evalCases = [s.strip() for s in evalCases.strip().split('\n')]
		for case in evalCases:
			assert valueForString(case) == eval(case), \
				'case=%r, valueForString()=%r, eval()=%r' \
					% (case, valueForString(case), eval(case))

		stringCases = [s.strip() for s in stringCases.strip().split('\n')]
		for case in stringCases:
			assert valueForString(case) == case, \
				'case=%r, valueForString()=%r' \
					% (case, valueForString(case))


	def testWordWrap(self):
		# an example with some spaces and newlines
		msg = """Arthur:  "The Lady of the Lake, her arm clad in the purest \
	shimmering samite, held aloft Excalibur from the bosom of the water, \
	signifying by Divine Providence that I, Arthur, was to carry \
	Excalibur. That is why I am your king!"

	Dennis:  "Listen. Strange women lying in ponds distributing swords is \
	no basis for a system of government. Supreme executive power derives \
	from a mandate from the masses, not from some farcical aquatic \
	ceremony!\""""

		for margin in range(20, 200, 20):
			s = wordWrap(msg, margin)
			for line in s.split('\n'):
				assert len(line) <= margin, \
					'len=%i, margin=%i, line=%r' % (len(line), margin, line)
