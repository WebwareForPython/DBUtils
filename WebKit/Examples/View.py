from ExamplePage import ExamplePage
import os

class View(ExamplePage):
	"""View the source of a WebKit servlet.

	For each WebKit example, you will see a sidebar with various menu items,
	one of which is "View source of <i>example</i>". This link points to the View
	servlet and passes the filename of the current servlet. The View servlet
	then loads that file's source code and displays it in the browser for
	your viewing pleasure.

	Note that if the View servlet isn't passed a filename, it prints the
	View's docstring which you are reading right now.

	"""

	def writeContent(self):
		req = self.request()
		if req.hasField('filename'):
			trans = self.transaction()
			fn = req.field('filename')
			if os.sep in fn:
				self.write('<h3 style="color:red">Error</h3><p>'
					'Cannot request a file outside of this directory %r</p>' % fn)
				return
			fn = self.request().serverSidePath(fn)
			self.request().fields()['filename'] = fn
			trans.application().forward(trans, 'Colorize.py')
		else:
			doc = self.__class__.__doc__.split('\n', 1)
			doc[1] = '</p>\n<p>'.join(doc[1].split('\n\n'))
			self.writeln('<h2>%s</h2>\n<p>%s</p>' % tuple(doc))
