"""
PySummary

A PySummary instance reads a Python file and creates a summary of the file
which you can access by using it as a (e.g., %s or str()).

The notion of a "category" is recognized. A category is simply a group of
methods with a given name. The default prefix for denoting a category is ##.

"""

from types import DictType
import os


class PySummary:


	## Init ##

	def __init__(self):
		self._filename = None
		self._lines = []
		self.invalidateCache()
		if os.path.exists('PySummary.config'):
			self.readConfig('PySummary.config')


	## Config ##

	def readConfig(self, filename):
		self._settings = eval(open(filename).read())
		assert type(self._settings) is DictType


	## Reading files ##

	def readFileNamed(self, filename):
		self._filename = filename
		file = open(filename)
		self.readFile(file)
		file.close()

	def readFile(self, file):
		self.invalidateCache()
		lines = file.readlines()
		while lines:
			line = lines.pop(0).rstrip()
			sline = line.lstrip()
			if not sline:
				continue
			try:
				if sline[:6] == 'class ' and sline[6] != '_' and (
					sline.find('(', 7) >= 0 or sline.find(':', 7) >= 0):
					self._lines.append(Line('class', line)) # a class
					line = lines.pop(0).lstrip()
					if line[:3] == '"""': # skip docstring
						while lines and line.rstrip()[-3:] != '"""':
							line = lines.pop(0)
					while lines and line.lstrip(): # skip body
						line = lines.pop(0)
				elif sline[:4] == 'def ' and (sline[4] != '_'
					or sline[5] == '_') and sline.find('(', 5) >= 0:
					self._lines.append(Line('def', line)) # a method
					line = lines.pop(0).lstrip()
					if line[:3] == '"""': # skip docstring
						while lines and line.rstrip()[-3:] != '"""':
							line = lines.pop(0)
					while lines and line.lstrip(): # skip body
						line = lines.pop(0)
				elif sline[:3] == '## ': # a category
					self._lines.append(Line('category', line))
			except IndexError:
				pass


	## Reports ##

	def text(self):
		return self.render('text')

	def html(self):
		return self.render('html')

	def render(self, format):
		filename = self._filename
		path, basename = os.path.split(filename)
		module = os.path.splitext(basename)[0]
		package = '%s.%s' % (path, module)
		span = format == 'html'
		settings = self._settings[format]
		res = []
		res.append(settings['file'][0] % locals())
		if self._lines:
			for line in self._lines:
				type = line.type()
				if line.text()[:1].lstrip() \
					and settings[type][0][:1] == '\n':
					res.append('\n')
				res.append(settings[type][0])
				if span:
					res.append('<span class="line_%s">' % type)
				res.append(getattr(line, format)()) # e.g., line.format()
				if span:
					res.append('</span>')
				res.append('\n')
				res.append(settings[type][1])
		else:
			res.append('# No classes or functions defined in this module.')
		res.append('\n')
		res.append(settings['file'][1] % locals())
		res = ''.join(res)
		res = res.replace('\t', settings['tabSubstitute'])
		return res


	## As strings ##

	def __repr__(self):
		return self.text()

	def __str__(self):
		return self.html()


	## Self utility ##

	def invalidateCache(self):
		self._text = None
		self._html = None


class Line:

	def __init__(self, type, contents):
		self._type = type
		self._text = contents
		self._html = None

	def type(self):
		return self._type

	def text(self):
		return self._text

	def html(self):
		if self._html is None:
			if self._type == 'class' or self._type == 'def':
				ht = self._text
				start = ht.find(self._type) + len(self._type) + 1
				end = ht.find('(', start)
				if end < 0:
					end = ht.find(':', start)
					if end < 0:
						end = start
				if self._type == 'def':
					end2 = ht.find(')', end + 1)
					if end2 >= 0:
						ht = ht[:end2+1]
				ht = '%s<span class="name_%s">%s</span>%s' % (
					ht[:start], self._type, ht[start:end], ht[end:])
			else:
				ht = self._text
			self._html = ht
		return self._html

	def __str__(self):
		return self.contents()


## Auxiliary functions ##


def test():
	print 'Testing on self...'
	sum = PySummary()
	sum.readFileNamed('PySummary.py')
	open('PySummary.py.sum.text', 'w').write(sum.text())
	open('PySummary.py.sum.html', 'w').write(sum.html())
	print 'Wrote PySummary.py.sum.* files.'
	print 'Finished.'


if __name__ == '__main__':
	test()
