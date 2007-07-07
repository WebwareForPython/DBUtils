import os, sys

from MiscUtils import StringIO
from WebKit.Page import Page


class Colorize(Page):
	"""Syntax highlights Python source files.

	Set a variable 'filename' in the request so I know which file to work on.
	This also demonstrates forwarding. The View servlet actually forwards
	its request here.

	"""

	def respond(self, transaction):
		"""Write out a syntax hilighted version of the file.

		The filename is an attribute of the request object.

		"""
		res = transaction._response
		req = self.request()
		if not req.hasField('filename'):
			res.write('<h3 style="color:red">Error</h3><p>'
				'No filename given to syntax color!</p>')
			return
		filename = req.field('filename')
		filename = self.request().serverSidePath(os.path.basename(filename))
		if not os.path.exists(filename):
			res.write('<h3 style="color:red">Error</h3><p>'
				'The requested file %r does not exist'
				' in the proper directory.</p>' % os.path.basename(filename))
			return
		from DocSupport import py2html
		myout = StringIO()
		stdout = sys.stdout
		sys.stdout = myout
		py2html.main((None, '-stdout', '-files', filename))
		results = myout.getvalue()
		results = results.replace('\t', '    ')  # 4 spaces per tab
		res.write(results)
		sys.stdout = stdout
