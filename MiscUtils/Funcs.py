"""
Funcs.py

Funcs.py, a member of MiscUtils, holds functions that don't fit in anywhere else.
"""

import md5, os, random, time, sys, tempfile
from struct import calcsize

try: # for Python < 2.3
	True, False
except NameError:
	True, False = 1, 0


def commas(number):
	"""Insert commas in a number.

	Return the given number as a string with commas to separate
	the thousands positions.

	The number can be a float, int, long or string. Returns None for None.

	"""
	if number is None:
		return None
	if not number:
		return str(number)
	number = list(str(number))
	if '.' in number:
		i = number.index('.')
	else:
		i = len(number)
	while 1:
		i -= 3
		if i <= 0 or number[i-1] == '-':
			break
		number[i:i] = [',']
	return ''.join(number)


def charWrap(s, width, hanging=0):
	"""Word wrap a string.

	Return a new version of the string word wrapped with the given width
	and hanging indent. The font is assumed to be monospaced.

	This can be useful for including text between <pre> </pre> tags,
	since <pre> will not word wrap, and for lengthly lines,
	will increase the width of a web page.

	It can also be used to help delineate the entries in log-style
	output by passing hanging=4.

	"""
	if not s:
		return s
	assert hanging < width
	hanging = ' ' * hanging
	lines = s.split('\n')
	i = 0
	while i < len(lines):
		s = lines[i]
		while len(s) > width:
			t = s[width:]
			s = s[:width]
			lines[i] = s
			i += 1
			lines.insert(i, None)
			s = hanging + t
		else:
			lines[i] = s
		i += 1
	return '\n'.join(lines)


def excstr(e):
	"""Return a string for the exception.

	The string will be in the format that Python normally outputs
	in interactive shells and such:
		<ExceptionName>: <message>
		AttributeError: 'object' object has no attribute 'bar'
	Neither str(e) nor repr(e) do that.

	"""
	if e is None:
		return None
	return '%s: %s' % (e.__class__.__name__, e)


# Python 2.3 contains mktemp and mkstemp, both of which accept a
# directory argument.  Earlier versions of Python only contained
# mktemp which didn't accept a directory argument.  So we have to
# implement our own versions here.
if sys.version_info >= (2, 3, None, None):
	# Just use the Python 2.3 built-in versions.
	from tempfile import mktemp, mkstemp
else:
	try:
		from tempfile import _counter
	except ImportError:
		class _Counter:
			def __init__(self):
				self._counter = 0
			def get_next(self):
				self._counter += 1
				return self._counter
		_counter = _Counter()

	def mktemp(suffix="", dir=None):
		"""User-callable function to return a unique temporary file name.

		Duplicated from Python's own tempfile with the optional "dir"
		argument added. This allows customization of the directory, without
		having to take over the module level variable, tempdir.

		"""
		if not dir:
			dir = tempfile.gettempdir()
		pre = tempfile.gettempprefix()
		while 1:
			i = _counter.get_next()
			file = os.path.join(dir, pre + str(i) + suffix)
			if not os.path.exists(file):
				return file

	def mkstemp(suffix="", dir=None):
		"""User-callable function to return an opened temporary file.

		The tuple will contain:
		- a os-level file handle for the temp file, open for read/write
		- the absolute path of that file

		Note that this version of the function is not as secure as the
		version included in Python 2.3.

		"""
		path = mktemp(suffix, dir)
		return os.open(path, os.O_RDWR|os.O_CREAT|os.O_EXCL, 0600), path


def wordWrap(s, width=78):
	"""Return a version of the string word wrapped to the given width.

	Respects existing newlines in the string.

	Taken from:
	http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/148061

	"""
	return reduce(
		lambda line, word, width=width: "%s%s%s" % (
			line,
			' \n'[(len(line[line.rfind('\n')+1:]) + len(word) >= width)],
			word
		),
		s.split(' ')
	)


def dateForEmail(now=None):
	"""Return a properly formatted date/time string for email messages."""
	if now is None:
		now = time.localtime(time.time())
	if now[8] == 1:
		offset = -time.altzone / 60
	else:
		offset = -time.timezone / 60
	if offset < 0:
		plusminus = '-'
	else:
		plusminus = '+'
	return time.strftime('%a, %d %b %Y %H:%M:%S ', now) \
		+ plusminus + '%02d%02d' % (abs(offset/60), abs(offset%60))


def hostName():
	"""Return the host name.

	The name is taken first from the os environment and failing that,
	from the 'hostname' executable. May return None if neither attempt
	succeeded. The environment keys checked are HOST and HOSTNAME,
	both upper and lower case.

	"""
	for name in ['HOST', 'HOSTNAME', 'host', 'hostname']:
		hostName = os.environ.get(name, None)
		if hostName:
			break
	if not hostName:
		hostName = os.popen('hostname').read().strip()
	if not hostName:
		hostName = None
	else:
		hostName = hostName.lower()
	return hostName


_localIP = None

def localIP(remote=('www.yahoo.com', 80), useCache=1):
	"""Get the "public" address of the local machine.

	This is the address which is connected to the general Internet.

	This function connects to a remote HTTP server the first time it is
	invoked (or every time it is invoked with useCache=0). If that is
	not acceptable, pass remote=None, but be warned that the result is
	less likely to be externally visible.

	Getting your local ip is actually quite complex. If this function
	is not serving your needs then you probably need to think deeply
	about what you really want and how your network is really set up.
	Search comp.lang.python for "local ip" for more information.
	http://groups.google.com/groups?q=%22local+ip%22+group:comp.lang.python.*

	"""
	global _localIP
	if useCache and _localIP:
		return _localIP
	import socket
	if remote:
		# code from Donn Cave on comp.lang.python

		# My notes:
		# Q: Why not use this? socket.gethostbyname(socket.gethostname())
		# A: On some machines, it returns '127.0.0.1' - not what we had in mind.
		#
		# Q: Why not use this? socket.gethostbyname_ex(socket.gethostname())[2]
		# A: Because some machines have more than one IP (think "VPN", etc.) and
		#    there is no easy way to tell which one is the externally visible IP.

		try:
			s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			s.connect(remote)
			ip, port = s.getsockname()
			s.close()
			_localIP = ip
			return _localIP
		except socket.error:
			# oh, well. we'll use the local method
			pass

	addresses = socket.gethostbyname_ex(socket.gethostname())[2]
	for address in addresses:
		if address != '127.0.0.1':
			if useCache:
				_localIP = address
			return address
	if useCache:
		_localIP = addresses[0]
	return _localIP


# Addresses can "look negative" on some boxes, some of the time. If you
# feed a "negative address" to an %x format, Python 2.3 displays it as
# unsigned, but produces a FutureWarning, because Python 2.4 will display
# it as signed. So when you want to prodce an address, use positive_id()
# to obtain it. _address_mask is 2**(number_of_bits_in_a_native_pointer).
# Adding this to a negative address gives a positive int with the same
# hex representation as the significant bits in the original.
# This idea and code were taken from ZODB (http://svn.zope.org).

_address_mask = 256L ** calcsize('P')

def positive_id(obj):
	"""Return id(obj) as a non-negative integer."""
	result = id(obj)
	if result < 0:
		result += _address_mask
		assert result > 0
	return result


def _descExc(reprOfWhat, e):
	"""Return a description of an exception.

	This is a private function for use by safeDescription().

	"""
	try:
		return '(exception from repr(%s): %s: %s)' % (reprOfWhat, e.__class__, e)
	except:
		return '(exception from repr(%s))' % reprOfWhat

def safeDescription(x, what='what'):
	"""Return the repr() of x and its class (or type) for help in debugging.

	A major benefit here is that exceptions from repr() are consumed.
	This is important in places like "assert" where you don't want
	to lose the assertion exception in your attempt to get more information.

	Example use:
	assert isinstance(foo, Foo), safeDescription(foo)
	print "foo:", safeDescription(foo)  # won't raise exceptions

	# better output format:
	assert isinstance(foo, Foo), safeDescription(foo, 'foo')
	print safeDescription(foo, 'foo')

	"""
	try:
		xRepr = repr(x)
	except Exception, e:
		xRepr = _descExc('x', e)
	if hasattr(x, '__class__'):
		try:
			cRepr = repr(x.__class__)
		except Exception, e:
			cRepr = _descExc('x.__class__', e)
		return '%s=%s class=%s' % (what, xRepr, cRepr)
	else:
		try:
			cRepr = repr(type(x))
		except Exception, e:
			cRepr = _descExc('type(x)', e)
		return '%s=%s type=%s' % (what, xRepr, cRepr)


def timestamp(numSecs=None):
	"""Return a dictionary whose keys give different versions of the timestamp.

	The dictionary will contain the following timestamp versions:
		'numSecs': the number of seconds
		'tuple': (year, month, day, hour, min, sec)
		'pretty': 'YYYY-MM-DD HH:MM:SS'
		'condensed': 'YYYYMMDDHHMMSS'
		'dashed': 'YYYY-MM-DD-HH-MM-SS'

	The focus is on the year, month, day, hour and second, with no additional
	information such as timezone or day of year. This form of timestamp is
	often ideal for print statements, logs and filenames. If the current number
	of seconds is not passed, then the current time is taken. The 'pretty'
	format is ideal for print statements, while the 'condensed' and 'dashed'
	formats are generally more appropriate for filenames.

	"""
	if numSecs is None:
		numSecs = time.time()
	tuple     = time.localtime(numSecs)[:6]
	pretty    = '%4i-%02i-%02i %02i:%02i:%02i' % tuple
	condensed = '%4i%02i%02i%02i%02i%02i' % tuple
	dashed    = '%4i-%02i-%02i-%02i-%02i-%02i' % tuple
	return locals()


def uniqueId(forObject=None):
	"""Generate an opaque, identifier string.

	The string is practically guaranteed to be unique
	If an object is passed, then its id() is incorporated into the generation.
	Relies on md5 and returns a 32 character long string.

	"""
	if hasattr(os, 'urandom'): # prefer os.urandom(), if available
		r = [os.urandom(8)]
	else:
		r = [time.time(), random.random(), os.times()]
	if forObject is not None:
		r.append(id(forObject))
	md5object = md5.new(str(r))
	try:
		return md5object.hexdigest()
	except AttributeError:
		# Older versions of Python didn't have hexdigest, so we'll do it manually
		hexdigest = []
		for char in md5object.digest():
			hexdigest.append('%02x' % ord(char))
		return ''.join(hexdigest)


def valueForString(s):
	"""Return value for a string.

	For a given string, returns the most appropriate Pythonic value
	such as None, a long, an int, a list, etc. If none of those
	make sense, then returns the string as-is.

	"None", "True" and "False" are case-insensitive because there is
	already too much case sensitivity in computing, damn it!

	"""
	if not s:
		return s
	try:
		return int(s)
	except ValueError:
		pass
	try:
		return long(s)
	except ValueError:
		pass
	try:
		return float(s)
	except ValueError:
		pass
	t = s.lower()
	if t == 'none':
		return None
	if t.lower() == 'true':
		return True
	if t.lower() == 'false':
		return False
	if s[0] in '[({"\'':
		return eval(s)
	return s


## Deprecated ##

def Commas(number):
	print 'DEPRECATED: MiscUtils.Funcs.Commas() on 02/23/01 in ver 0.5. Use commas() instead.'
	return commas(number)

def CharWrap(s, width, hanging=0):
	print 'DEPRECATED: MiscUtils.Funcs.CharWrap() on 02/23/01 in ver 0.5. Use charWrap() instead.'
	return charWrap(s, width, hanging)
