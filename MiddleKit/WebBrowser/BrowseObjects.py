from StorePage import StorePage


class BrowseObjects(StorePage):

	def writeContent(self):
		className = self.request().field('class')
		self.writeln(self.store().htObjectsOfClassNamed(className))
