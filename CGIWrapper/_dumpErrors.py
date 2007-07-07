from _dumpCSV import _dumpCSV


class _dumpErrors(_dumpCSV):

	def cellContents(self, rowIndex, colIndex, value):
		"""
		This is a hook for subclasses to customize the
		contents of a cell based on any criteria (including
		location).
		"""
		if self._headings[colIndex] == 'error report filename':
			return '<a href="%s">%s</a>' % (value, value)
		else:
			return value
