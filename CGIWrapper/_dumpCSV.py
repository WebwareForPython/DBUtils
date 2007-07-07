import os, string
from AdminPage import *


def LoadCSV(filename):
	"""
	Loads a CSV (comma-separated value) file from disk and returns
	it as a list of rows where each row is a list of values (which
	are always strings).
	"""
	f = open(filename)
	rows = []
	while 1:
		line = f.readline()
		if not line:
			break
		rows.append(string.split(line, ','))
	f.close()
	return rows


class _dumpCSV(AdminPage):

	def __init__(self, dict):
		AdminPage.__init__(self, dict)
		self._filename = self._fields['filename'].value

	def shortFilename(self):
		return os.path.splitext(os.path.split(self._filename)[1])[0]

	def title(self):
		return 'View ' + self.shortFilename()

	def writeBody(self):
		rows = LoadCSV(self._filename)

		self.writeln('<p><table align=center border=0 cellpadding=2 cellspacing=2 bgcolor=#EEEEEE>')

		# Head row gets special formatting
		self._headings = map(lambda name: string.strip(name), rows[0])
		self.writeln('<tr bgcolor=black>')
		for value in self._headings:
			self.writeln('<td><font face="Arial, Helvetica" color=white><b> ', value, ' </b></font></td>')
		self.writeln('</tr>')

		# Data rows
		rowIndex = 1
		for row in rows[1:]:
			self.writeln('<tr>')
			colIndex = 0
			for value in row:
				self.writeln('<td> ', self.cellContents(rowIndex, colIndex, value), ' </td>')
				colIndex += 1
			self.writeln('</tr>')
			rowIndex += 1

		self.writeln('</table>')

	def cellContents(self, rowIndex, colIndex, value):
		"""
		This is a hook for subclasses to customize the
		contents of a cell based on any criteria (including
		location).
		"""
		return value
