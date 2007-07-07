import os, sys

sys.path.insert(1, os.path.abspath('../..'))

from WebUtils.HTMLTag import HTMLReader
from MiscUtils import StringIO

#from MiscUtils import unittest
import unittest


class HTMLTagTest(unittest.TestCase):

	def setUp(self):
		self._html = """\
<html>
	<head>
		<title>Example</title>
	</head>
	<body color=white bgcolor=#000000>
		<p> What's up, <i>doc</i>? </p>
		<hr>
		<table id=dataTable>
			<tr> <th> x </th> <th> y </th> </tr>
			<tr> <td class=datum> 0 </td> <td class=datum> 0 </td> </tr>
		</table>
	</body>
</html>"""

	def checkBasics(self):
		reader = HTMLReader()
		tag = reader.readString('<html> </html>')
		assert tag.name() == 'html'
		assert reader.rootTag() == tag
		assert reader.filename() is None
		out = StringIO()
		tag.pprint(out)
		assert out.getvalue() == '<html>\n</html>\n'

	def checkReuseReader(self):
		reader = HTMLReader()
		reader.readString('<html> </html>')
		tag = reader.readString('<html> <body> </body> </html>')
		assert reader.rootTag() is not None
		assert reader.rootTag() == tag

		tag = reader.readString('<html> </html>', retainRootTag=0)
		assert tag is not None
		assert reader.rootTag() is None

	def checkAccess(self):
		html = HTMLReader().readString(self._html)

		# Name
		assert html.name() == 'html'

		# Attrs
		assert html.numAttrs() == 0
		assert not html.hasAttr('foo')
		self.assertRaises(KeyError, html.attr, 'foo')
		assert html.attr('foo', None) is None

		# Children and subtags, when both are the same.
		for numFoos, fooAt, foos in [
				[html.numChildren, html.childAt, html.children],
				[html.numSubtags, html.subtagAt, html.subtags]]:
			assert numFoos() == 2
			assert len(foos()) == 2
			assert fooAt(0).name() == 'head'
			assert fooAt(1).name() == 'body'

		# Children and subtags when they're different
		body = html.subtagAt(1)
		p = body.subtagAt(0)
		assert p.name() == 'p'
		assert p.numChildren() == 3
		assert p.numSubtags() == 1

	def checkMatchingAttr(self):
		html = HTMLReader().readString(self._html)
		assert html.tagWithMatchingAttr('color', 'white').name() == 'body'
		assert html.tagWithMatchingAttr('id', 'dataTable').name() == 'table'
		assert html.tagWithId('dataTable').name() == 'table'

	def checkInvalidHTML(self):
		from WebUtils.HTMLTag import HTMLTagUnbalancedError, HTMLTagIncompleteError

		reader = HTMLReader()

		html = '<html> <body> <table> </body> </html>'
		self.assertRaises(HTMLTagUnbalancedError, reader.readString, html)

		html = '<html> <body>'
		self.assertRaises(HTMLTagIncompleteError, reader.readString, html)

	def tearDown(self):
		del self._html


def makeTestSuite():
	cases = ['Basics', 'ReuseReader', 'Access', 'MatchingAttr', 'InvalidHTML']
	tests = [HTMLTagTest('check'+case) for case in cases]
	return unittest.TestSuite(tests)


if __name__ == '__main__':
	runner = unittest.TextTestRunner(stream=sys.stdout)
	unittest.main(defaultTest='makeTestSuite', testRunner=runner)
