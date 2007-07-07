from ExamplePage import ExamplePage


class Forward(ExamplePage):

	def writeContent(self):
		trans = self.transaction()
		resp = self.response()
		resp.write("<p>This is the Forward servlet speaking. I am now"
			" going to include the output of the <i>Welcome</i> servlet"
			" via Application's <tt>includeURL()</tt> method:</p>")
		trans.application().includeURL(trans, 'Welcome.py')
