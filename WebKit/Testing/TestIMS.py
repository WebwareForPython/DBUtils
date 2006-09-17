from WebKit.SidebarPage import SidebarPage

class TestIMS(SidebarPage):

	def cornerTitle(Self):
		return 'Testing'

	def error(self, msg):
		self.write('<p style="color:red">%s</p>' % self.htmlEncode(msg))

	def writemsg(self, msg):
		self.write('<p>%s</p>' % self.htmlEncode(msg))

	def writetest(self, msg):
		self.write('<h4>%s</h4>' % msg)

	def getdoc(self, path, headers={}):
		con = self._httpconnection(self._host)
		con.request('GET', path, headers=headers)
		return con.getresponse()

	def writeContent(self):
		import httplib
		sd = self.request().serverDictionary()
		self._host = sd['HTTP_HOST'] # includes the port
		self._httpconnection = sd.get('HTTPS', '').lower() == 'on' \
			and  httplib.HTTPSConnection or httplib.HTTPConnection
		adapter = self.request().adapterName()
		self.write('<h2>Test If-Modified-Since support in Webware</h2>')
		# pick a static file which is served up by Webwares UnknownFileHandler
		self.runtest('%s/PSPExamples/psplogo.png' % adapter)

	def runtest(self, path):
		import time
		self.writetest('Opening <tt>%s</tt>' % path)
		rsp = self.getdoc(path)
		originalsize = size = len(rsp.read())
		if rsp.status != 200:
			self.error('Expected status of 200, received %s.' % rsp.status)
			return
		if size > 0:
			self.writemsg('Received: %s %s, document size = %s (as expected).'
				% (rsp.status, rsp.reason, size))
		else:
			self.error('Document size is: %d' % size)
			return
		lm = rsp.getheader('Last-Modified', '')
		if lm:
			self.writemsg('Last modified: %s' % lm)
		else:
			self.error('No Last-Modified header found.')
			return
		# Retrieve document again with IMS and expect a 304 not modified
		self.writetest('Opening <tt>%s</tt><br>with If-Modified-Since: %s' % (path, lm))
		rsp = self.getdoc(path, {'If-Modified-Since': lm})
		size = len(rsp.read())
		if rsp.status != 304:
			self.error('Expected status of 304, received %s.' % rsp.status)
			return
		if size:
			self.error('Expected 0 length document, received %d bytes.' % size)
			return
		else:
			self.writemsg('Received %s %s, document size = %s (as expected).'
				% (rsp.status, rsp.reason, size))
		arpaformat = '%a, %d %b %Y %H:%M:%S GMT'
		t = list(time.strptime(lm, arpaformat))
		t[0] = t[0] - 1 # last year
		newlm = time.strftime(arpaformat, time.gmtime(time.mktime(t)))
		self.writetest('Opening <tt>%s</tt><br>with If-Modified-Since: %s'
			% (path, newlm))
		rsp = self.getdoc(path, {'If-Modified-Since': newlm})
		size = len(rsp.read())
		lm = rsp.getheader('Last-Modified', '')
		self.writemsg('Last modified: %s' % lm)
		if rsp.status != 200:
			self.error('Expected status of 200, received %s %s.'
				% (rsp.status, rsp.reason))
			return
		if size != originalsize:
			self.error('Received: %s %s, document size = %s,'
				' expected size = %s.'
				% (rsp.status, rsp.reason, size, originalsize))
			return
		else:
			self.writemsg('Received: %s %s, document size = %s (as expected).'
				% (rsp.status, rsp.reason, size))
		self.writetest('%s passed.' % self.__class__.__name__)
