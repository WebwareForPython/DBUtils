
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
<li>you must have the PostgreSQL database</li>
<li>and the PyGreSQL adapter installed, and</li>
<li>you must have created a database with the name "demo" and</li>
<li>a database user with the name "demo" and password "demo".</li>
</ul>
<p><a href="DBUtilsExample">Start the demo!</a></p>
''')
