# ADOSample.py
#
# Simple example of using ADO in WebKit for database access with
# automatic connection pooling.
#
# To run this example, you'll have to set EnableCOM to 1 in the
# AppServer.config file; you'll have to create a database with a table
# called Customers that has a CustomerName field; and you'll
# have to create a System DSN called MyDataSource that points to
# that database.  Then, install this file in the WebKit/Examples
# directory and try it out.  It ought to work with any database
# accessible through ODBC and/or ADO.
#
# The recordset function below should go into a base class so it
# can be shared among many servlets.

from win32com.client import Dispatch
from ExamplePage import ExamplePage


class ADOSample(ExamplePage):

	def recordset(self, sql):
		# Open an ADO connection
		conn = Dispatch('ADODB.Connection')
		conn.Open('MyDataSource')
		# Store the connection in the Application object.  We're never going to
		# USE this stored connection, but we're saving it so that we'll always
		# have at least one connection to this data source open.  ADO
		# will automatically pool connections to a given data source as long as
		# at least one connection to that data source remains open at all times,
		# so doing this significantly increases the speed of opening
		# the connection the next time this function is called.
		self.application().MyDataSource_connection = conn
		# Open and return the requested recordset
		rs = Dispatch('ADODB.Recordset')
		rs.Open(sql, conn)
		return rs

	def writeContent(self):
		# Grab some data from the database and display it
		rs = self.recordset('SELECT CustomerName FROM Customers ORDER BY CustomerName')
		self.writeln('<h1>ADO Sample</h1>')
		self.writeln('<h3>Your Customers are:</h3>')
		self.writeln('<ul>')
		while not rs.EOF:
			self.writeln('<li>%s</li>' % rs.Fields('CustomerName').Value)
			rs.MoveNext()
		self.writeln('</ul>')
