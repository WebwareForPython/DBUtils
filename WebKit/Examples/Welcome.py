from ExamplePage import ExamplePage


class Welcome(ExamplePage):

	def writeContent(self):
		wr = self.writeln
		wr('<h2>Welcome to WebKit %s!</h2>' % self.application().webKitVersionString())
		path = self.request().servletPath()
		wr('''\
		<p> Along the side of this page you will see various links that will take you to:</p>
		<ul>
			<li>The different WebKit examples.</li>
			<li>The source code of the current example.</li>
			<li>Whatever contexts have been configured.
				Each context represents a distinct set of web pages,
				usually given a descriptive name.</li>
			<li>External sites, such as the Webware home page.</li>
		</ul>
		<p>The <a href="%(path)s/Admin/">Admin</a> context is particularly interesting because
		it takes you to the administrative pages for the WebKit application server where
		you can review logs, configuration, plug-ins, etc.</p>
		<p>The <a href="%(path)s/Docs/">Docs</a> contexts allow you to browse
		the documentation of <a href="%(path)s/WebKit/Docs/">WebKit</a>
		and <a href="%(path)s/Docs/ComponentIndex.html">all other components</a>
		of Webware for Python.</p>''' % locals())
		from os.path import join
		wr('<p>The location of the documentation on the server:</p>')
		wr('<ul>')
		wr('<li>WebKit: <tt>%s</tt></li>'
			% join(self.application().webKitPath(), 'Docs'))
		wr('<li>Webware for Python: <tt>%s</tt></li>'
			% join(self.application().webwarePath(), 'Docs'))
		wr('</ul>')
		req = self.request()
		extraURLPath = req.extraURLPath()
		if extraURLPath and extraURLPath != '/':
			wr('''
			<p><b>Note:</b> extraURLPath information was found on the URL,
			and a servlet was not found to process it.
			Processing has been delegated to this servlet.</p>''')
			wr('<ul>')
			wr('<li>serverSidePath: <tt>%s</tt></li>'
				% req.serverSidePath())
			wr('<li> extraURLPath: <tt>%s</tt></li>' % extraURLPath)
			wr('</ul>')