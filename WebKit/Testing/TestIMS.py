import time
from WebKit.SidebarPage import SidebarPage


class TestIMS(SidebarPage):

	def cornerTitle(Self):
		return 'Testing'

	def error(self, msg):
		self.write('<p style="color:red">%s</p>' % self.htmlEncode(msg))

	def writeMsg(self, msg):
		self.write('<p>%s</p>' % self.htmlEncode(msg))

	def writeTest(self, msg):
		self.write('<h4>%s</h4>' % msg)

	def getDoc(self, path, headers={}):
		con = self._httpconnection(self._host)
		con.request('GET', path, headers=headers)
		return con.getresponse()

	def writeContent(self):
		import httplib
		sd = self.request().serverDictionary()
		self._host = sd['HTTP_HOST'] # includes the port
		self._httpconnection = sd.get('HTTPS', '').lower() == 'on' \
			and  httplib.HTTPSConnection or httplib.HTTPConnection
		servletPath = self.request().servletPath()
		self.write('<h2>Test If-Modified-Since support in Webware</h2>')
		# pick a static file which is served up by Webwares UnknownFileHandler
		self.runTest('%s/PSP/Examples/psplogo.png' % servletPath)

	def runTest(self, path):
		self.writeTest('Opening <tt>%s</tt>' % path)
		rsp = self.getDoc(path)
		originalSize = size = len(rsp.read())
		if rsp.status != 200:
			self.error('Expected status of 200, received %s.' % rsp.status)
			return
		if size > 0:
			self.writeMsg('Received: %s %s, document size = %s (as expected).'
				% (rsp.status, rsp.reason, size))
		else:
			self.error('Document size is: %d' % size)
			return
		lm = rsp.getheader('Last-Modified', '')
		if lm:
			self.writeMsg('Last modified: %s' % lm)
		else:
			self.error('No Last-Modified header found.')
			return
		# Retrieve document again with IMS and expect a 304 not modified
		self.writeTest('Opening <tt>%s</tt><br>with If-Modified-Since: %s' % (path, lm))
		rsp = self.getDoc(path, {'If-Modified-Since': lm})
		size = len(rsp.read())
		if rsp.status != 304:
			self.error('Expected status of 304, received %s.' % rsp.status)
			return
		if size:
			self.error('Expected 0 length document, received %d bytes.' % size)
			return
		else:
			self.writeMsg('Received %s %s, document size = %s (as expected).'
				% (rsp.status, rsp.reason, size))
		arpaformat = '%a, %d %b %Y %H:%M:%S GMT'
		try:
			t = list(time.strptime(lm, arpaformat))
		except AttributeError: # this can happen for Python < 2.3 on Windows
			self.error('Python version does not support time.strptime, sorry.')
			return
		t[0] -= 1 # last year
		newlm = time.strftime(arpaformat, time.gmtime(time.mktime(t)))
		self.writeTest('Opening <tt>%s</tt><br>with If-Modified-Since: %s'
			% (path, newlm))
		rsp = self.getDoc(path, {'If-Modified-Since': newlm})
		size = len(rsp.read())
		lm = rsp.getheader('Last-Modified', '')
		self.writeMsg('Last modified: %s' % lm)
		if rsp.status != 200:
			self.error('Expected status of 200, received %s %s.'
				% (rsp.status, rsp.reason))
			return
		if size != originalSize:
			self.error('Received: %s %s, document size = %s, '
				'expected size = %s.'
				% (rsp.status, rsp.reason, size, originalSize))
			return
		else:
			self.writeMsg('Received: %s %s, document size = %s (as expected).'
				% (rsp.status, rsp.reason, size))
		self.writeTest('%s passed.' % self.__class__.__name__)
