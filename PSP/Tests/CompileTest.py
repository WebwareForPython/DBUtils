"""
	Automated tests for PSP Kit

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

import os
import imp
import logging
import unittest
from PSP import Context, PSPCompiler
from MiscUtils import StringIO

# There is a circular dependency between AppServer and Application in imports
# so I have to import both AppServer before Page imports Application.
import WebKit.AppServer

_log = logging.getLogger(__name__)

# Turn off debug messages, and delete temporary scripts after test:
DEBUG = 0
if DEBUG:
	logging.basicConfig()
	_log.setLevel(logging.DEBUG)


class CompileTest(unittest.TestCase):

	def compileString(self, pspSource, classname):
		'''Compile a string to an object.

		Takes a string, compiles it, imports the Python file, and returns you
		the Python class object.

		classname = some string so that each file is unique per test case.
		'''
		# write string to temporary file
		moduleName = "tmp_CompileTest_" + classname
		tmpInName = moduleName + ".psp"
		tmpOutName = moduleName + ".py"
		_log.debug('Writing PSP source to: "%s"', tmpInName)
		fp = open(tmpInName, 'w')
		fp.write(pspSource)
		fp.close()
		# Compile PSP into .py file
		context = Context.PSPCLContext(tmpInName)
		context.setClassName(classname)
		context.setPythonFileName(tmpOutName)
		clc = PSPCompiler.Compiler(context)
		clc.compile()
		# Have Python import the .py file.
		fp = open(tmpOutName)
		if fp:
			try:
				description = ('.py', 'r', imp.PY_SOURCE)
				theModule = imp.load_module(moduleName, fp, tmpOutName, description)
			finally:
				# Since we may exit via an exception, close fp explicitly.
				fp.close()
		if not DEBUG:
			os.remove(tmpInName)
			os.remove(tmpOutName)
			os.remove(moduleName + ".pyc")
		# want to return the class inside the module.
		theClass = getattr(theModule, classname)
		return theClass

	def compileAndRun(self, pspSource, classname):
		pspClass = self.compileString(pspSource, classname)
		pspInstance = pspClass()
		outStream = StringIO()
		pspInstance._writeHTML(outStream)
		output = outStream.getvalue()
		return output

	def testExpression(self):
		output = self.compileAndRun('two plus three is: <%= 2+3 %>', 'testExpression')
		self.assertEquals("two plus three is: 5", output)

	def testScript(self):
		output = self.compileAndRun('one plus two is: <% res.write(str(1+2)) %>', 'testScript')
		self.assertEquals("one plus two is: 3", output)

	def testScript_NewLines(self):
		psp = '''\nthree plus two is: \n<%\nres.write(str(3+2)) \n%>'''
		expect = '''\nthree plus two is: \n5'''
		output = self.compileAndRun(psp, 'testScript_NewLines')
		self.assertEquals(output, expect)
		psp = '''\nthree plus two is: \n<%\n  res.write(str(3+2)) \n%>'''
		expect = '''\nthree plus two is: \n5'''
		output = self.compileAndRun(psp, 'testScript_NewLines')
		self.assertEquals(output, expect)

	def testScript_Returns(self):
		psp = '''\rthree plus two is: \r<%\rres.write(str(3+2)) \r%>'''
		expect = '''\nthree plus two is: \n5'''
		output = self.compileAndRun(psp, 'testScript_Returns')
		self.assertEquals(output, expect)
		psp = '''\rthree plus two is: \r<%\r     res.write(str(3+2)) \r%>'''
		expect = '''\nthree plus two is: \n5'''
		output = self.compileAndRun(psp, 'testScript_Returns')
		self.assertEquals(output, expect)

	def testScript_If(self):
		psp = '''PSP is <% if 1: %>Good<% end %>'''
		expect = '''PSP is Good'''
		output = self.compileAndRun(psp, 'testScript_If')
		self.assertEquals(output, expect)

	def testScript_IfElse(self):
		psp = '''JSP is <% if 0: %>Good<% end %><% else: %>Bad<% end %>'''
		expect = '''JSP is Bad'''
		output = self.compileAndRun(psp, 'testScript_IfElse')
		self.assertEquals(output, expect)

	def testScript_Blocks(self):
		psp = '''
<% for i in range(3): %>
	<%= i %><br/>
<% end %>'''
		expect = '''

	0<br/>

	1<br/>

	2<br/>
'''
		output = self.compileAndRun(psp, 'testScript_Blocks')
		self.assertEquals(output, expect)

	def testScript_Braces(self):
		psp = '''\
<%@page indentType="braces" %>
<% for i in range(3): { %>
	<%= i %><br/>
<% } %>'''
		expect = '''

	0<br/>

	1<br/>

	2<br/>
'''
		output = self.compileAndRun(psp, 'testScript_Braces')
		self.assertEquals(output, expect)

	def testPspMethod(self):
		psp = '''
		<psp:method name="add" params="a,b">
		return a+b
		</psp:method>
		7 plus 8 = <%= self.add(7,8) %>
		'''
		output = self.compileAndRun(psp, 'testPspMethod').strip()
		self.assertEquals("7 plus 8 = 15", output)

	def testPspFile(self):
		psp = '''
		<psp:file>
			def square(a):
				return a*a
		</psp:file>
		7^2 = <%= square(7) %>
		'''
		output = self.compileAndRun(psp, 'testPspFile').strip()
		self.assertEquals("7^2 = 49", output)

	def testPspClass(self):
		psp = '''
		<psp:class>
			def square(self, a):
				return a*a
		</psp:class>
		4^2 = <%= self.square(4) %>
		'''
		output = self.compileAndRun(psp, 'testPspClass').strip()
		self.assertEquals("4^2 = 16", output)
