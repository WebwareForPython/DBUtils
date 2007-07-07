from WebKit.Page import Page
from WebUtils.Funcs import htmlEncode


class Inspector(Page):

	def writeContent(self):
		req = self.request()
		self.write('Path:<br>\n')
		self.write('<tt>%s</tt><p>\n'
				% htmlEncode(req.extraURLPath()))
		self.write('Variables:<br>\n')
		self.write('<table border=1>')
		names = req.fields().keys()
		names.sort()
		for name in names:
			self.write('<tr><td align=right>%s:</td><td>%s</td></tr>\n'
				% (htmlEncode(name), htmlEncode(req.field(name))))
		self.write('</table><p>\n')
		self.write('Server-side path:<br>\n')
		self.write('<tt>%s</tt><p>\n' % req.serverSidePath())
