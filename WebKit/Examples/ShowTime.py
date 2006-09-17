from ExamplePage import ExamplePage
from time import *


class ShowTime(ExamplePage):

	def writeContent(self):
		self.write('<h4>The current time is:</h4>')
		self.write('<h5 style="color:green">', asctime(localtime(time())), '</h5>')
