from WebKit.Examples.ExamplePage import ExamplePage
import os
from glob import glob

class KidExamplePage(ExamplePage):

	def title(self):
		try:
			title = os.path.splitext(os.path.basename(
				self._orig_file))[0]
		except AttributeError:
			title = 'Kid Example'
		return title

	def cornerTitle(self):
		return "Kid Examples"

	def scripts(self):
		"""Create list of dictionaries with info about a particular script."""
		examples = []
		filesyspath = self.request().serverSidePath()
		files = glob(os.path.join(os.path.dirname(filesyspath), "*.kid"))
		for i in files:
			file = os.path.split(i)[1]
			script = {}
			script['pathname'] = script['name'] = file
			examples.append(script)
		return examples

	def writeOtherMenu(self):
		self.menuHeading('Other')
		viewPath = self.request().uriWebKitRoot() + "KidKitExamples/View"
		self.menuItem('View source of<br/>%s' % self.title(),
			self.request().uriWebKitRoot() +
				'KidKitExamples/View?filename=%s'
				% os.path.basename(self.request().serverSidePath()))
		if self.application().hasContext('Documentation'):
			filename = 'Documentation/WebKit.html'
			if os.path.exists(filename):
				self.menuItem('Local WebKit docs',
					self.request().adapterName() + '/' + filename)
