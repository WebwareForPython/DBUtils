import os
from KidKit.Examples.KidExamplePage import KidExamplePage


class View(KidExamplePage):
	"""View the source of a Kid template.

	For each Kid example, you will see a sidebar with various menu items,
	one of which is "View source of <i>example</i>". This link points to the View
	servlet and passes the filename of the current servlet. The View servlet
	then loads that Kid file's source code and displays it in the browser for
	your viewing pleasure.

	Note that if the View servlet isn't passed a Kid filename, it prints the
	View's docstring which you are reading right now.

	"""

	def writeContent(self):
		req = self.request()
		if req.hasField('filename'):
			filename = req.field('filename')
			basename = os.path.basename(filename)
			filename = self.request().serverSidePath(basename)
			if not os.path.exists(filename):
				self.write('<p style="color:red">'
					'No such file %r exists</p>' % basename)
				return
			text = open(filename).read()
			text = self.htmlEncode(text)
			text = text.replace('\n', '<br>').replace('\t', ' '*4)
			self.write('<pre>%s</pre>' % text)
		else:
			doc = self.__class__.__doc__.split('\n', 1)
			doc[1] = '</p>\n<p>'.join(doc[1].split('\n\n'))
			self.writeln('<h2>%s</h2>\n<p>%s</p>' % tuple(doc))
