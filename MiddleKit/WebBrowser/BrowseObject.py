from StorePage import StorePage


class BrowseObject(StorePage):

	def writeContent(self):
		req = self.request()
		className = req.field('class')
		serialNum = int(req.field('serialNum'))
		obj = self.store().fetchObject(className, serialNum, None)
		if obj is None:
			self.writeln('<p>No object in store for %s.%i.</p>'
				% (className, serialNum))
		else:
			wr = self.writeln
			wr('<table border="1">')
			wr(obj.klass().htHeadingsRow())
			wr(obj.htAttrsRow())
			wr('</table>')
