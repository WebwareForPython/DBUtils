from WebKit.SidebarPage import SidebarPage
import os


class ExamplePage(SidebarPage):
	"""WebKit page template class for displaying examples.

	The convention for picking up examples from WebKit plug-ins is:
		* Properties.py must have at least this:
			WebKitConfig = {
				'examplePages': [],
			}

		  But usually specifies various pages:
		    WebKitConfig = {
		    	'examplesPages': [
		    		'foo',
		    		'bar',
		    	]
		    }
		* The plug-in must have an Examples/ directory.
		* That directory must have an index.* or Main.* which
		  inherits from ExamplePage.
		* The implementation can pass in which case a menu of
		  the pages for that plug-in is written:
		    # Main.py
		    from WebKit.Examples.ExamplePage import ExamplePage
		    class Main(ExamplePage):
		    	pass

	If WebKitConfig['examplesPages'] is non-existant or None, then
	no examples will be available for the plug-in.

	If the WebKit Examples context is not present in the first place,
	then there is no access to the plug-in examples.

	"""

	def cornerTitle(self):
		return 'WebKit Examples'

	def isDebugging(self):
		return 0

	def examplePages(self, plugInName=None):
		"""Get a list of all example pages.

		Returns a list of all the example pages for our particular plug-in.
		These can be used in the sidebar or in the main content area to
		give easy access to the other example pages.

		"""
		if plugInName is None:
			# Special case: We're in WebKit examples
			from WebKit.Properties import WebKitConfig
			return WebKitConfig['examplePages']
		else:
			# Any other plug-in:
			plugIn = self.application().server().plugIn(plugInName)
			return plugIn.examplePages()

	def writeSidebar(self):
		self.writeExamplesMenu()
		self.writeOtherMenu()
		self.writeWebKitSidebarSections()

	def writeExamplesMenu(self):
		servletPath = self.request().servletPath()
		self.menuHeading('Examples')
		ctx = self.request().contextName().split('/', 2)
		plugIns = self.application().server().plugIns()
		plugInName = len(ctx) > 1 and ctx[1] == 'Examples' and ctx[0]
		# WebKit
		self.menuItem('WebKit', '%s/Examples/' % servletPath)
		if not plugInName:
			self.writeExamplePagesItems()
		# Other plug-ins
		for plugIn in plugIns:
			if plugIn.hasExamplePages():
				name = plugIn.name()
				link = '%s/%s/' % (servletPath, plugIn.examplePagesContext())
				self.menuItem(name, link)
				if name == plugInName:
					self.writeExamplePagesItems(name)

	def writeExamplePagesItems(self, pluginName=None):
		for page in self.examplePages(pluginName):
			self.menuItem(page, page, indentLevel=2)

	def writeOtherMenu(self):
		self.menuHeading('Other')
		viewPath = self.request().uriWebKitRoot() + "Examples/View"
		self.menuItem(
			'View source of<br>%s' % self.title(),
			self.request().uriWebKitRoot() + 'Examples/View?filename=%s' \
				% os.path.basename(self.request().serverSidePath()))
		if self.application().hasContext('Documentation'):
			filename = 'Documentation/WebKit.html'
			if os.path.exists(filename):
				self.menuItem('Local WebKit docs',
					self.request().servletPath() + '/' + filename)

	def title(self):
		return self.request().contextName()

	def writeContent(self):
		wr = self.writeln
		wr('<div style="padding-left:2em"><table>')
		for page in self.examplePages(
				self.request().contextName().split('/', 1)[0]):
			wr('<tr><td bgcolor="#E8E8F0"><a href=%s>%s</a>'
				'</td></tr>' % (page, page))
		wr('</table></div>')
