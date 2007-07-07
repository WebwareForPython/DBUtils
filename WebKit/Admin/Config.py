from AdminSecurity import AdminSecurity
from WebUtils import Funcs


class Config(AdminSecurity):

	def title(self):
		return 'Config'

	def writeContent(self):
		self.heading('AppServer')
		self.writeln(Funcs.htmlForDict(self.application().server().config()))

		self.heading('Application')
		self.writeln(Funcs.htmlForDict(self.application().config()))

	def heading(self, heading):
		self.writeln('<h4 style="background-color:#555;color:white;'
			'padding:2pt;margin:1px;margin-top:12pt">%s</h4>' % heading)
