from KidExamplePage import KidExamplePage


class Main(KidExamplePage):

	def respond(self, trans):
		from WebKit.URLParser import ServletFactoryManager
		for factory in ServletFactoryManager._factories:
			if factory.name().startswith('KidServlet'):
				trans.application().forward(trans, 'Welcome')
		KidExamplePage.respond(self, trans)

	def writeContent(self):
		self.writeln('''<h4 style="color:red">Kid templates not installed.</h4>
<p>The KidKit plug-in is based on the <tt>kid</tt> package available at
<a href="http://www.kid-templating.org">www.kid-templating.org</a>.</p>''')
