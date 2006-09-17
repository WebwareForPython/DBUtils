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
<a href="http://kid.lesscode.org">kid.lesscode.org</a>.</p>
<p>Please note that <tt>kid</tt> in turn requires
the <tt>ElementTree</tt> package available at
<a href="http://effbot.org/downloads/#elementtree">effbot.org/downloads/#elementtree</a>.</p>
<p>You may also want to install the <tt>cElementTree</tt> package from
<a href="http://effbot.org/downloads/#cElementTree">effbot.org/downloads/#cElementTree</a>
in order to enhance the performance.</p>''')
