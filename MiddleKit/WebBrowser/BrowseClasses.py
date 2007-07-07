from StorePage import StorePage


class BrowseClasses(StorePage):

	def writeContent(self):
		self.writeln('<p>Click a class on the left'
			' to browse all objects of that class.</p>')
