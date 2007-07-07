"""
	Automated tests for PSPUtils

	(c) Copyright by Winston Wolff, 2004 http://www.stratolab.com

	Permission to use, copy, modify, and distribute this software and its
	documentation for any purpose and without fee or royalty is hereby granted,
	provided that the above copyright notice appear in all copies and that
	both that copyright notice and this permission notice appear in
	supporting documentation or portions thereof, including modifications,
	that you make.

	THE AUTHORS DISCLAIM ALL WARRANTIES WITH REGARD TO
	THIS SOFTWARE, INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY AND
	FITNESS, IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY SPECIAL,
	INDIRECT OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING
	FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT,
	NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION
	WITH THE USE OR PERFORMANCE OF THIS SOFTWARE !

"""

import unittest
from PSP import PSPUtils

if 0:
	import doctest

	def suite():
		"""Combine our unittest with our doctests."""
		result = unittest.TestSuite()
		result.addTest(doctest.DocTestSuite(PSPUtils))
		result.addTest(unittest.defaultTestLoader.loadTestsFromTestCase(PSPUtilsTest))
		return result


class PSPUtilsTest(unittest.TestCase):

	def testNormalizeIndentation(self):

		before = """
            def add(a,b):
              return a+b"""
		expected = \
"""
def add(a,b):
  return a+b"""

		self.assertEquals(PSPUtils.normalizeIndentation(before), expected)

		# Comments should be ignored for the unindentation
		before = """
# Will comments throw off the indentation?
            def add(a,b):
              return a+b"""
		expected = \
"""
# Will comments throw off the indentation?
def add(a,b):
  return a+b"""

		self.assertEquals(PSPUtils.normalizeIndentation(before), expected)

		# Will blank lines cause a problem?
		before = """
# Will blank lines cause a problem?

            def add(a,b):

              return a+b"""
		expected = \
"""
# Will blank lines cause a problem?

def add(a,b):

  return a+b"""

		self.assertEquals(PSPUtils.normalizeIndentation(before), expected)

		# Different line endings OK?
		before = '#line endings\r  def add(a,b):\r  \r  return a+b'
		expected = '#line endings\rdef add(a,b):\r\rreturn a+b'

		self.assertEquals(PSPUtils.normalizeIndentation(before), expected)

	def testSplitLines(self):

		text = 'one\rtwo\rthree'
		self.assertEquals(3, len(PSPUtils.splitLines(text)))

		text = 'one\ntwo\nthree'
		self.assertEquals(3, len(PSPUtils.splitLines(text)))

