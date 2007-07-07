"""FieldStorage.py

This module defines a subclass of the standard Python cgi.FieldStorage class
with an extra method that will allow a FieldStorage to parse a query string
even in a POST request.

"""


import cgi, os, urllib


class FieldStorage(cgi.FieldStorage):

	def __init__(self, fp=None, headers=None, outerboundary="",
			environ=os.environ, keep_blank_values=0, strict_parsing=0):
		self._environ = environ
		self._strict_parsing = strict_parsing
		self._keep_blank_values = keep_blank_values
		cgi.FieldStorage.__init__(self, fp, headers, outerboundary,
			environ, keep_blank_values, strict_parsing)

	def parse_qs(self):
		"""Explicitly parse the query string, even if it's a POST request."""
		self._method = self._environ.get('REQUEST_METHOD', '').upper()
		if self._method == "GET" or self._method == "HEAD":
			# print __file__, "bailing on GET or HEAD request"
			return # bail because cgi.FieldStorage already did this
		self._qs = self._environ.get('QUERY_STRING', None)
		if not self._qs:
			# print __file__, "bailing on no query_string"
			return # bail if no query string

		r = {}
		for name_value in self._qs.split('&'):
			nv = name_value.split('=', 2)
			if len(nv) != 2:
				if self._strict_parsing:
					raise ValueError, "bad query field: %r" % (name_value,)
				continue
			name = urllib.unquote(nv[0].replace('+', ' '))
			value = urllib.unquote(nv[1].replace('+', ' '))
			if len(value) or self._keep_blank_values:
				if r.has_key(name):
					r[name].append(value)
				else:
					r[name] = [value]

		# Only append values that aren't already in the FieldStorage's keys;
		# This makes POSTed vars override vars on the query string
		if not self.list:
			# This makes sure self.keys() are available, even
			# when valid POST data wasn't encountered.
			self.list = []
		for key, values in r.items():
			if not self.has_key(key):
				for value in values:
					self.list.append(cgi.MiniFieldStorage(key, value))
