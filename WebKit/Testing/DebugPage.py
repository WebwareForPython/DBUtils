from WebKit.Page import Page

class DebugPage(Page):

	def getstate(self):
		_evars = ('PATH_INFO', 'REQUEST_URI', 'SCRIPT_NAME')
		_pvars = ('_absolutepath', '_adapterName',
			'_contextName', '_extraURLPath',  '_originalURLPath',
			'_serverSidePath', '_serverSideContextPath')
		req = self.request()
		env = req._environ
		rv = []
		for key in _evars:
			rv.append("  * env['%s'] = %s"
				% (key, env.get(key, "* no def *")))
		for key in _pvars:
			rv.append("  * req.%s = %s"
				% (key, getattr(req, key, "* no def *")))
		return '\n'.join(rv)

	def writeContent(self):
		self.writeln('<h2><tt>%s</tt></h2>' % self.__class__.__name__ )
		self.writeln('<pre>%s</pre>' % self.getstate())
