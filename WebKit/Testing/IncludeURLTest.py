from WebKit.Page import Page


class IncludeURLTest(Page):
	"""Test includeURL redirection.

	This test will test out the callMethodOfServlet and includeURL
	redirection. The forward() method works similar to these but is
	not tested here. The following operations are performed:

	The form fields are displayed, as seen by this servlet.

	The request environment of this servlet is displayed.

	The writeStatus method on the servlet IncludeURLTest2 which is
	found in the Dir subdirectory under Testing is called.

	The title method is called on several other servlets to demonstrate
	calling methods on servlets in different areas relative to here.

	Finally, the top level page of this context is included with includeURL.

	A 'Test Complete' message is displayed at the very end.

	"""

	def writeBody(self):
		self.writeln('<body style="margin:6pt;font-family:sans-serif">')
		fields = self.request().fields()
		self.writeln('<h2>%s</h2>' % self.__class__.__name__)
		self.writeln('<h3>class = <tt>%s</tt>, module= <tt>%s</tt></h3>' %
			(self.__class__.__name__, self.__module__))
		self.writeln('<p>%s</p>' %
			self.__class__.__doc__.replace('\n\n', '</p><p>'))
		self.writeln('<h4>Number of fields in the request.fields(): %d</h4>'
			% len(fields))
		self.writeln('<ul>')
		for key, value in fields.items():
			self.writeln('<li>%s = %s</li>'
				% (self.htmlEncode(key), self.htmlEncode(value)))
		self.writeln('</ul>')
		self.writeStatus()
		self.cmos('/Testing/Dir/IncludeURLTest2', 'writeStatus',
			"Expect to see the status written by IncludeURLTest2"
			" which is the same format as the above status,"
			" only relative to /Testing/Dir.")
		self.cmos('Dir/IncludeURLTest2', 'serverSidePath',
			"This returns the serverSide Path of the"
			" Dir/IncludeURLTest2 servlet. Notice that there is"
			" no leading '/' which means this test is relative to"
			" the current directory.")
		self.cmos('/Testing/', 'name',
			"This returns the name of the module at the top of"
			" the Testing context which is 'Main'.")
		self.cmos('/Testing/Main', 'serverSidePath',
			"This returns the serverSidePath of the servlet"
			" accessed at the top of this context.")
		self.cmos('Main', 'serverSidePath',
			"This returns the serverSidePath of the servlet"
			" accessed 'Main' and should be the same as the"
			" servlet accessed through the Testing context.")
		self.writeln('<h4>Including Dir/IncludeURLTest2:</h4>')
		self.write('<div style="margin-left:2em">')
		self.includeURL('Dir/IncludeURLTest2')
		self.write('</div>')
		self.writeln("<h4>Including the Main servlet of the %s context:</h4>"
			% self.request().contextName())
		self.write('<div style="margin-left:2em">')
		self.includeURL('Main')
		self.write('</div>')
		self.writeln('<h4>%s complete.</h4>' % self.__class__.__name__)
		self.writeln('</body>')

	def writeStatus(self):
		self.writeln('<h4>Request Status of <tt>%s</tt>:</h4>'
			% self.__class__.__name__)
		w = self.w
		req = self.request()
		env = req._environ
		self.writeln("<pre>")
		w("serverSidePath():        %s" % req.serverSidePath())
		w("adapterName():           %s" % req.adapterName())
		w("servletPath():           %s" % req.servletPath())
		w("contextName():           %s" % req.contextName())
		w("serverSideContextPath(): %s" % req.serverSideContextPath())
		w("extraURLPath():          %s" % req.extraURLPath())
		w("urlPath():               %s" % req.urlPath())
		w("previousURLPaths():      %s" % ', '.join(req.previousURLPaths()))
		w("Environment:")
		w("REQUEST_URI:             %s" % env.get('REQUEST_URI', ''))
		w("PATH_INFO:               %s" % env.get('PATH_INFO', ''))
		w("SCRIPT_NAME:             %s" % env.get('SCRIPT_NAME', ''))
		w("SCRIPT_FILENAME:         %s" % env.get('SCRIPT_FILENAME', ''))
		self.writeln('</pre>')

	def w(self, msg):
		self.writeln(self.htmlEncode(msg))

	def cmos(self, url, method, desc):
		app = self.application()
		trans = self.transaction()
		self.writeln('<p>Calling'
			' <tt>callMethodOfServlet(t, "%s", "%s")</tt>:</p>'
			'<p>%s</p>' % (url, method, desc))
		self.write('<div style="margin-left:2em">')
		ret = app.callMethodOfServlet(trans, url, method)
		self.write('</div>')
		self.writeln('<p><tt>callMethodOfServlet</tt> returned %s.</p>'
			% (ret is not None and '<tt>%s</tt>'
					% self.htmlEncode(repr(ret)) or 'nothing'))
