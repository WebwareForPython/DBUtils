from StorePage import StorePage


class BrowseList(StorePage):

	def writeContent(self):
		req = self.request()
		className = req.field('class')
		serialNum = int(req.field('serialNum'))
		obj = self.store().fetchObject(className, serialNum, None)
		attrName = req.field('attr')
		self.writeln('<p><a href="BrowseObject?class=%(className)s'
			'&serialNum=%(serialNum)s">%(className)s.%(serialNum)s</a>'
			' <b>%(attrName)s</b></p>' % locals())
		self.writeln(obj.htObjectsInList(attrName))
