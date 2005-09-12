from WebKit.Examples.ExamplePage import ExamplePage


class Main(ExamplePage):

	def writeContent(self):
		self.writeln('''<h2>DBUtils example</h2>
<p>You can set the DBUtils parameters in the following file</p>
<ul>
<li><tt>Configs/Database.config</tt></li>
</ul>
<p>With the default settings,</p>
<ul>
<li>you must have the PostgreSQL database installed</li>
<li>you must have created a database with the name "demo"</li>
<li>the Application server user must have access to "demo"</li>
<li>the PyGreSQL adapter must be installed</li>
</ul>
<p><a href="DBUtilsExample">Start the demo!</a></p>
''')
