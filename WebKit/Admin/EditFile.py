from WebKit.Page import Page


class EditFile(Page):

	def writeHTML(self):
		res = self.response()
		res.setHeader('Content-type', 'application/x-webkit-edit-file')
		field = self.request().field
		# @@ ib 3/03: more information should be added about this Webware
		# installation, so that the client program could handle multiple
		# installations with different file locations.
		res.write('Filename: %s\n' % field('filename'))
		res.write('Line: %s\n' % field('line'))
