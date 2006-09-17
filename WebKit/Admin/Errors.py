from DumpCSV import DumpCSV

class Errors(DumpCSV):

	def filename(self):
		return self.application().setting('ErrorLogFilename')

	def cellContents(self, rowIndex, colIndex, value):
		"""Hook for subclasses to customize the contents of a cell.

		Based on any criteria (including location).

		"""
		if self._headings[colIndex] in ('pathname', 'error report filename'):
			return '<a href="file:///%s">%s</a>' % (value, value)
		elif self._headings[colIndex] == 'time':
			return '<span style="white-space:nowrap">%s</span>' % (value)
		else:
			return value
