import FixPath


import unittest
from MiscUtils.CSVParser import CSVParser, ParseError


class CSVParserTests(unittest.TestCase):
	"""
	TO DO

	* Test the different options for parser. See CVSParser.__init__
	"""

	def setUp(self):
		self.parse = CSVParser().parse

	def testNegatives(self):
		inputs = [
			'""a',
			'"a"b',
			'a\n,b'
		]
		for input in inputs:
			try:
				results = self.parse(input)
			except ParseError:
				pass
			else:
				print
				print 'results:', repr(results)
				raise Exception, 'Did not get an exception for: %r' % input

	def testPositives(self):
		tests = [
			# basics
			('', []),
			(',', ['', '']),
			(',,', ['', '', '']),
			('a', ['a']),
			('a,b', ['a', 'b']),
			('a,b,c,d,e,f', 'a b c d e f'.split()),

			# surrounding whitespace
			(' a', ['a']),
			('a ', ['a']),
			(' a ', ['a']),
			('a, b', ['a', 'b']),
			('  a  ,  b  ', ['a', 'b']),

			# commas in fields
			('","', [',']),
			('",",","', [',', ',']),
			('"a  ,  b",b', ['a  ,  b', 'b']),

			# quotes in fields
			('""""', ['"']),
			('""""""', ['""']),
			('"""a""",b,"""c"""', ['"a"', 'b', '"c"']),

			# single line combos
			(' "a", "b"', ['a', 'b']),
			('  """"', ['"']),
			('""""  ', ['"']),
			('  """"  ', ['"']),
			(' """a""",  """b"""', ['"a"', '"b"']),
			('  """",  ",",   ""","""', ['"', ',', '","']),

			# comments
			('#a,b', []),

			# multiple line records
			('"a\nb"', ['a\nb']),
			('a,"b\nc"', ['a', 'b\nc']),
			('a,"b\nc\n\n\n"', ['a', 'b\nc']),

			# MiddleKit enums
			('a,Enums="b"', ['a', 'Enums="b"']),
			("a,Enums='b'", ['a', "Enums='b'"]),
			('a,"Enums=""b, c"""', ['a', 'Enums="b, c"']),
			('''a,"Enums='b, c'"''', ['a', "Enums='b, c'"]),
		]
		for input, output in tests:
			if input.find('\n') == -1:
				# single line
				result = self.parse(input)
				assert result == output, '\ninput=%r\nresult=%r\noutput=%r'\
					% (input, result, output)
				result = self.parse(input+'\n')
				assert result == output, '\ninput=%r\nresult=%r\noutput=%r' \
					% (input, result, output)
			else:
				# multiple lines
				gotFields = 0
				for line in input.split('\n'):
					assert not gotFields
					result = self.parse(line)
					if result is not None:
						gotFields = 1
				assert gotFields
				assert result == output, '\ninput=%r\nresult=%r\noutput=%r' \
					% (input, result, output)

def main():
	suite = unittest.makeSuite(CSVParserTests, 'test')
	runner = unittest.TextTestRunner()
	runner.run(suite)

if __name__ == '__main__':
	main()
