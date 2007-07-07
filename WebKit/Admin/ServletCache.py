import os, time
from Queue import Queue

from AdminSecurity import AdminSecurity
from WebUtils.Funcs import htmlEncode


class ServletCache(AdminSecurity):
	"""Display servlet cache.

	This servlet displays, in a readable form, the internal data
	structure of the cache of all servlet factories.

	This can be useful for debugging WebKit problems and the
	information is interesting in general.

	"""

	def title(self):
		return 'Servlet Cache'

	def writeContent(self):
		from WebKit.URLParser import ServletFactoryManager
		factories = filter(lambda f: f._classCache,
			ServletFactoryManager._factories)
		req = self.request()
		wr = self.writeln
		if len(factories) > 1:
			factories.sort()
			wr('<h3>Servlet Factories:</h3>')
			wr('<table cellspacing="2" cellpadding="2">')
			for factory in factories:
				wr('<tr><td><a href="#%s">%s</a></td></tr>'
					% ((factory.name(),)*2))
			wr('</table>')
		wr('<form method="post">')
		for factory in factories:
			name = factory.name()
			wr('<a name="%s"></a><h4>%s</h4>' % ((name,)*2))
			if req.hasField('flush_' + name):
				factory.flushCache()
				wr('<p style="color:green">'
					'The servlet cache has been flushed. &nbsp; '
					'<input type="submit" name="reload" value="Reload"></p>')
				continue
			wr(htCache(factory))
		wr('</form>')

def sortSplitFilenames(a, b):
	"""Custom comparison function for file names.

	This is a utility function for list.sort() that handles list elements
	that come from os.path.split. We sort first by base filename and then
	by directory, case insensitive.

	"""
	result = cmp(a['base'].lower(), b['base'].lower())
	if result == 0:
		result = cmp(a['dir'].lower(), b['dir'].lower())
	return result

def htCache(factory):
	"""Output the cache of a servlet factory."""
	html = []
	wr = html.append
	cache = factory._classCache
	keys = cache.keys()
	keys.sort()
	wr('<p>Uniqueness: %s</p>' % factory.uniqueness())
	wr('<p>Extensions: %s</p>' % ', '.join(map(repr, factory.extensions())))
	wr('<p>Unique paths in the servlet cache: <strong>%d</strong>'
		' &nbsp; <input type="submit" name="flush_%s" value="Flush"></p>'
		% (len(keys), factory.name()))
	wr('<p>Click any link to jump to the details for that path.</p>')
	wr('<h5>Filenames:</h5>')
	wr('<table cellspacing="2" cellpadding="2">')
	wr('<tr><th style="background-color:#DDD">File</th>'
		'<th style="background-color:#DDD">Directory</th></tr>')
	paths = []
	for key in keys:
		dir, base = os.path.split(key)
		path = {'dir': dir, 'base': base, 'full': key}
		paths.append(path)
	paths.sort(sortSplitFilenames)
	# At this point, paths is a list where each element is a tuple
	# of (basename, dirname, fullPathname) sorted first by basename
	# and second by dirname
	for path in paths:
		wr('<tr><td style="background-color:#EEE">'
			'<a href="#%s">%s</a></td>'
			'<td style="background-color:#EEE">%s</td></tr>'
			% (id(path['full']), path['base'], path['dir']))
	wr('</table>')
	wr('<h5>Full paths:</h5>')
	wr('<table cellspacing="2" cellpadding="2">')
	for key in keys:
		wr('<tr><td style="background-color:#EEE">'
			'<a href="#%s">%s</a></td></tr>' % (id(key), key))
	wr('</table>')
	wr('<h5>Details:</h5>')
	wr('<table cellpadding="2" cellspacing="2">')
	for path in paths:
		wr('<tr><td colspan="2" style="background-color:#EEF">'
			'<a name="%s"></a><p><strong>%s</strong> - %s</a></p></td></tr>'
			% (id(path['full']), path['base'], path['dir']))
		record = cache[path['full']].copy()
		record['path'] = path['full']
		if factory._threadsafeServletCache.has_key(path['full']):
			record['instances'] = 'one servlet instance (threadsafe)'
		else:
			record['instances'] = ('free reusable servlets: %d'
				% len(factory._servletPool))
		wr(htRecord(record))
	wr('</table>')
	return '\n'.join(html)

def htRecord(record):
	html = []
	wr = html.append
	keys = record.keys()
	keys.sort()
	for key in keys:
		htKey = htmlEncode(key)
		# determine the HTML for the value
		value = record[key]
		htValue = None
		# check for special cases where we want a custom display
		if hasattr(value, '__name__'):
			htValue = value.__name__
		if key == 'mtime':
			htValue = '%s (%s)' % (time.asctime(time.localtime(value)),
				str(value))
		# the general case:
		if not htValue:
			htValue = htmlEncode(str(value))
		wr('<tr><th style="background-color:#DDD">%s</th>'
			'<td style="background-color:#EEE">%s</td></tr>'
			% (htKey, htValue))
	return '\n'.join(html)
