from ExamplePage import ExamplePage


class RequestInformation(ExamplePage):
	"""Request information demo."""

	def writeContent(self):
		self.writeln('<h3>Request Variables</h3>')
		self.writeln('<p>The following table'
			' shows the values for various request variables.</p>')
		self.writeln('<table style="font-size:small;width:100%"'
			' border="0" cellpadding="2" cellspacing="2" width="100%">')
		request = self.request()
		self.dict('fields()', request.fields())
		self.dict('environ()', request.environ())
		self.dict('cookies()', request.cookies())
		self.writeln('</table>')
		setCookie = self.response().setCookie
		setCookie('TestCookieName', 'CookieValue')
		setCookie('TestExpire1', 'expires in 1 minute', expires='+1m')

	def pair(self, key, value):
		valueType = type(value)
		if valueType is type([]) or valueType is type(()):
			value = ', '.join(map(str, value))
		self.writeln('<tr valign="top"><td>%s</td><td>%s</td></tr>'
			% (key, self.htmlEncode(str(value))))

	def list(self, codeString):
		list = eval(codeString)
		assert type(list) is type([])  or  type(list) is type(())
		self.pair(codeString, list)

	def dict(self, name, dict):
		self.writeln('<tr valign="top">'
			'<td style="background-color:#CCF" colspan="2">%s</td>'
			'</tr>' % (name))
		keys = dict.keys()
		keys.sort()
		for name in keys:
			self.writeln('<tr valign="top" style="background-color:#EEF">'
				'<td>%s</td><td>%s</td></tr>' % (name, self.htmlEncode(
				str(dict[name])).replace('\n', '<br>').replace(
				',', ',<wbr>').replace(';', ';<wbr>').replace(':/', ':<wbr>/')))
