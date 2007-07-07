from DumpCSV import DumpCSV


class Access(DumpCSV):

	def filename(self):
		return self.application().setting('ActivityLogFilename')
