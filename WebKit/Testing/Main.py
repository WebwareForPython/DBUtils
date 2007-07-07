from WebKit.SidebarPage import SidebarPage
from WebKit.Application import Application
import os


class Main(SidebarPage):
	"""Testing - read TestCases.data and display them.

	TO DO
		* Reload TestCases.data only load when modified (by checking mod date).

	"""

	def title(self):
		return 'Testing'

	def cornerTitle(self):
		return 'WebKit Testing'

	def writeContent(self):
		self.writeln('<h2 style="text-align:center">Test cases</h2>')
		self.writeTestCases()
		self.writeNotes()

	def writeTestCases(self):
		wr = self.writeln
		req = self.request()
		servletPath = req.servletPath()
		filename = self.serverSidePath('TestCases.data')
		self._cases = self.readFileNamed(filename)
		wr('<table align="center" style="margin-left:auto;margin-right:auto"'
			' border="0" cellpadding="3" cellspacing="2">')
		wr('<tr style="color:white;background-color:#555">'
			'<td>#</td><td>URL</td><td>Expectation</td></tr>')
		caseNum = 1
		for case in self._cases:
			# For each URL, fix it up and make a name. Put in urls list.
			urls = []
			for url in case['URLs']:
				url = servletPath + url
				if url:
					urlName = self.htmlEncode(url)
					urls.append((url, urlName))
			if not urls:
				continue
			expectation = case['Expectation'] # self.htmlEncode(case['Expectation'])
			bgcolor = ['EEE', 'DDD'][caseNum % 2]
			wr('<tr style="background-color:#%s">'
				'<td>%d.</td><td>' % (bgcolor, caseNum))
			for url, urlName in urls:
				wr('<a href=%s>%s</a><br>' % (url, urlName))
			wr('<td>%s</td></tr>' % expectation)
			caseNum += 1
		wr('</table>')

	def readFileNamed(self, filename):
		"""Return a list of test cases.

		Each of them is a dictionary, as defined the given file.
		See TestCases.data for information on the format.

		"""
		f = open(filename)
		cases = self.readFile(f)
		f.close()
		return cases

	def readFile(self, file):
		return self.readContent(file.read())

	def readContent(self, content):
		lines = map(lambda line: line.strip(), content.split('\n'))
		lineNum = 1
		cases = []
		urls = []
		for line in lines:
			if line and line[0] != '#':
				if line[-1] == '\\': # continuation line;
					# means there are multiple URLs for this case
					urls.append(line[:-1].strip())
				else:
					parts = line.split('-->')
					if len(parts) != 2:
						self.error('Invalid line at %d.' % lineNum)
					urls.append(parts[0].strip())
					cases.append({
						'URLs': urls,
						'Expectation': parts[1].strip(),
					})
					urls = [] # reset list of URLs
			lineNum += 1
		return cases

	def writeNotes(self):
		self.writeln('''<h4>Notes</h4>
<ul>
<li>Test all links in all pages of all contexts (Examples, Admin, Testing, etc.),
including links found in the headers and footers of the pages.</li>
<li>Test functionality of interactive pages, like CountVisits and ListBox.</li>
<li>Test each link more than once.</li>
<li>Test with multiple adapters (WebKit.cgi, OneShot.cgi, etc.).</li>
</ul>''')

	def error(self, msg):
		raise Exception, msg
