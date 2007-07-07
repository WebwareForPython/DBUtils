"""HTMLTag.py

HTMLTag defines a class of the same name that represents HTML content. An
additional HTMLReader class kicks off the process of reading an HTML file into a
set of tags:

    from WebUtils.HTMLTag import HTMLReader
    reader = HTMLReader()
    tag = reader.readFileNamed('foo.html')
    tag.pprint()

Tags have attributes and children, which makes them hierarchical. See HTMLTag
class docs for more info.

Note that you imported HTMLReader instead of HTMLTag. You only need the latter
if you plan on creating tags directly.

You can discard the reader immediately if you like:

    tag = HTMLReader().readFileNamed('foo.html')

The point of reading HTML into tag objects is so that you have a concrete,
Pythonic data structure to work with. The original motiviation for such a beast
was in building automated regression test suites that wanted granular,
structured access to the HTML output by the web application.

See the doc string for HTMLTag for examples of what you can do with tags.


CAVEATS

* HTMLReader needs special attention with regards to tags like <p> and <li>
which sometimes are closed (</p> </li>) and sometimes not. See its doc string
for full information.

* HTMLReader is picky about the correctness of the HTML you feed it. Again see
the class docs for full info.


TO DO

* See the TO DO sections for each class.


CREDITS

* I didn't grok how to write an SGMLParser subclass until I read the very small
example by Sean McGrath at http://www.digitome.com/html2pyx.py (which I believe
is broken for empty tags).

* Determined what HTML tags are empty by scanning O'Reilly's HTML Pocket
Reference.

"""

# - report line numbers for errors
# - extra checking about what tags are allowed or disallowed inside other tags
# - minor tweaks

# Check for Python 2.0
import sys
pyVer = getattr(sys, 'version_info', None)
if pyVer is None or pyVer[0] < 2:
	raise Exception, 'HTMLTag requires Python 2.0 or greater.'

try: # for Python < 2.3
	True, False
except NameError:
	True, False = 1, 0

runFast = True
	# if enabled, overrides some key SGMLParser methods for more speed.
	# changing this has no effect once the module is imported (unless you reload())

from sgmllib import SGMLParser
from MiscUtils import NoDefault, AbstractError
from types import StringType


class HTMLTagError(Exception):

	def __init__(self, msg, **values):
		Exception.__init__(self, msg)
		self.values = values.copy()

class HTMLTagAttrLookupError(HTMLTagError, LookupError): pass
class HTMLTagUnbalancedError(HTMLTagError): pass
class HTMLNotAllowedError(HTMLTagError): pass
class HTMLTagProcessingInstructionError(HTMLTagError): pass
class HTMLTagIncompleteError(HTMLTagError): pass


DefaultEmptyTags = 'area basefont base bgsound br col colgroup frame hr' \
	' img input isindex link meta spacer wbr'.split()


class HTMLTag:
	"""
	Tags essentially have 4 major attributes:
		* name
		* attributes
		* children
		* subtags

	Name is simple:
		print tag.name()

	Attributes are dictionary-like in nature:
		print tag.attr('color')  # throws an exception if no color
		print tag.attr('bgcolor', None)  # returns none if no bgcolor
		print tag.attrs()

	Children are all the leaf parts of a tag, consisting of other tags and strings
	of character data.
		print tag.numChildren()
		print tag.childAt(0)
		print tag.children()

	Subtags is a convenient list of only the tags in the children:
		print tag.numSubtags()
		print tag.subtagAt(0)
		print tag.subtags()

	You can search a tag and all the tags it contains for a tag with a particular
	attribute matching a particular value:
		print tag.tagWithMatchingAttr('width', '100%')

	An HTMLTagAttrLookupError is raised if no matching tag is found. You can avoid
	this by providing a default value:
		print tag.tagWithMatchingAttr('width', '100%', None)

	Looking for specific 'id' attributes is common in regression testing (it allows
	you to zero in on logical portions of a page), so a convenience method is
	provided:
		tag = htmlTag.tagWithId('accountTable')


	TO DO

	* A walker() method for traversing the tag tree.
	* Search for a subtag with a given name, recursive or not.
	* Attribute traversal with dotted notation?
	* Do we need to convert tag names and attribute names to lower case, or does
	  SGMLParser already do that?
	* Should attribute values be strip()ed?
	  Probably not. SGMLParser probably strips them already unless they really do
	  have spaces as in "  quoted  ". But that's speculation.
	"""


	## Init and reading ##

	def __init__(self, name, lineNumber=None):
		assert '\n' not in name
		self._name = name
		self._attrs = {}
		self._children = []
		self._subtags = []
		self._lineNumber = lineNumber
		self._isClosed = False  # used by closedBy() and __repr__. helps with HTMLReader error messages

	def readAttr(self, name, value):
		"""
		Sets an attribute of the tag with the given name and value. An assertion
		fails if an attribute is set twice.
		"""
		assert not self._attrs.has_key(name), 'name = %r, attrs = %r' % (name, attrs)
		self._attrs[name] = value

	def addChild(self, child):
		"""
		Adds a child to the receiver. The child will be another tag or a string
		(CDATA).
		"""
		assert isinstance(child, HTMLTag) or type(child) is StringType, \
			'Invalid child: %r' % child
		self._children.append(child)
		if isinstance(child, HTMLTag):
			self._subtags.append(child)


	## Access ##

	def name(self):
		return self._name

	def attr(self, name, default=NoDefault):
		if default is NoDefault:
			return self._attrs[name]
		else:
			return self._attrs.get(name, default)

	def hasAttr(self, name):
		return self._attrs.has_key(name)

	def attrs(self):
		return self._attrs

	def numAttrs(self):
		return len(self._attrs)

	def childAt(self, index):
		return self._children[index]

	def numChildren(self):
		return len(self._children)

	def children(self):
		return self._children

	def subtagAt(self, index):
		return self._subtags[index]

	def numSubtags(self):
		return len(self._subtags)

	def subtags(self):
		return self._subtags


	## Printing ##

	def pprint(self, out=None, indent=0):
		if out is None:
			out = sys.stdout
		wr = out.write
		spacer = ' '*4*indent
		wr('%s<%s>\n' % (spacer, self._name))
		for key, value in self._attrs.items():
			wr('%s  %s = %s\n' % (spacer, key.ljust(12), value))
		indent += 1
		for child in self._children:
			if isinstance(child, HTMLTag):
				child.pprint(out, indent)
			else:
				wr('%s    %s\n' % (spacer, child))
		wr('%s</%s>\n' % (spacer, self._name))
		# ^^^
		# Printing a closing tag for an empty tag (such as <br>)
		# doesn't make much sense, but then it's a good reminder that
		# certain tags like <p> are closed immediately.

	def __repr__(self):
		r = ['<', self._name]
		if self._attrs:
			keys = self._attrs.keys()
			keys.sort()
			for key in keys:
				r.extend([' ', key, '="', self._attrs[key], '"'])
		r.append('>')
		if self._lineNumber or self._isClosed:
			r.append(' (')
			if self._lineNumber:
				r.append('%s' % self._lineNumber)
			if self._isClosed:
				if self._lineNumber:
					r.append('; ')
				r.append('closed by %s at %s' % (self._closedBy, self._closedAt))
			r.append(')')
		r = ''.join(r)
		return r


	## Searching ##

	def tagWithMatchingAttr(self, name, value, default=NoDefault):
		"""
		Performs a depth-first search for a tag with an attribute that matches the
		given value. If the tag cannot be found, a KeyError will be raised *unless* a
		default value was specified, which is then returned.
			tag = tag.tagWithMatchingAttr('bgcolor', '#FFFF', None)
		"""
		tag = self._tagWithMatchingAttr(name, value)
		if tag is None:
			if default is NoDefault:
				raise HTMLTagAttrLookupError('name = %r, value = %r' % (name, value), name=name, value=value)
			else:
				return default
		else:
			return tag


	def tagWithId(self, id, default=NoDefault):
		"""
		Finds and returns the tag with the given id. As in:
			<td id=foo> bar </td>
		This is just a cover for:
			tagWithMatchingAttr('id', id, default)
		But searching for id's is so popular (at least in regression testing web
		sites) that this convenience method is provided.
		Why is it so popular? Because by attaching ids to logical portions of your
		HTML, your regression test suite can quickly zero in on them for examination.
		"""
		return self.tagWithMatchingAttr('id', id, default)


	## Parsing (HTMLReader) ##

	def closedBy(self, name, lineNumber):
		self._isClosed = True
		self._closedBy = name
		self._closedAt = lineNumber


	## Self utility ##

	def _tagWithMatchingAttr(self, name, value):
		"""
		Performs a depth-first search for a tag with an attribute that matches the
		given value. Returns None if the tag cannot be found.
		The method tagWithMatchingAttr() (e.g., sans underscore) is more commonly
		used.
		"""
		if self._attrs.get(name, None) == value:
			return self
		for tag in self._subtags:
			matchingTag = tag._tagWithMatchingAttr(name, value)
			if matchingTag:
				return matchingTag
		return None


class HTMLReader(SGMLParser):
	"""
	NOTES

	* Special attention is required regarding tags like <p> and <li> which
	  sometimes are closed and sometimes not. HTMLReader can deal with both situations
	  (closed and not) provided that:
		* the file doesn't change conventions for a given tag
		* the reader knows ahead of time what to expect

	Be default, HTMLReader assumes that <p> and <li> will be closed with </p> and
	</li> as the official HTML spec, as well as upcomer XHTML, encourage or require,
	respectively.

	But if your files don't close certain tags that are supposed to be required,
	you can do this:
		HTMLReader(extraEmptyTags=['p', 'li'])
	or:
		reader.extendEmptyTags(['p', 'li'])

	Or just set them entirely:
		HTMLReader(emptyTags=['br', 'hr', 'p'])
		reader.setEmptyTags(['br', 'hr', 'p'])
	Although there are quite a few. Consider the DefaultEmptyTags global list
	(which is used to initialize the reader's tags) which contains about 16 tag
	names.

	If an HTML file doesn't conform to the reader's expectation, you will get an
	exception (see more below for details).

	If your HTML file doesn't contain root <html> ... </html> tags wrapping
	everything, a fake root tag will be constructed for you, unless you pass
	in fakeRootTagIfNeeded=False.

	Besides fixing your reader manually, you could conceivably loop through the
	permutations of the various empty tags to see if one of them resulted in a
	correct read.

	Or you could fix the HTML.

	* The reader ignores extra preceding and trailing whitespace by stripping it
	  from strings. I suppose this is a little harsher than reducing spans of
	  preceding and trailing whitespace down to one space, which is what really
	  happens in an HTML browser.

	* The reader will not read past the closing </html> tag.

	* The reader is picky about the correctness of the HTML you feed it. If tags
	  are not closed, overlap (instead of nest) or left unfinished, an exception is
	  thrown. These include HTMLTagUnbalancedError, HTMLTagIncompleteError and
	  HTMLNotAllowedError which all inherit HTMLTagError.

	  This pickiness can be quite useful for the validation of the HTML of your
	  own applications.

	  I believe it is possible that others kinds of HTML errors could raise
	  exceptions from sgmlib.SGMLParser (from which HTMLReader inherits),
	  although in practice, I have not seen them.


	TO DO

	* Could the "empty" tag issue be dealt with more sophistication by
	  automatically closing <p> and <li> (e.g., popping them off the _tagStack) when
	  other major tags were encountered such as <p>, <li>, <table>, <center>, etc.?

	* Readers don't handle processing instructions: <? foobar ?>.

	* The tagContainmentConfig class var can certainly be expanded for even better
	  validation.
	"""


	## Init ##

	def __init__(self, emptyTags=None, extraEmptyTags=None, fakeRootTagIfNeeded=True):
		SGMLParser.__init__(self)
		self._filename  = None
		self._rootTag   = None
		self._fakeRootTagIfNeeded = fakeRootTagIfNeeded
		self._usedFakeRootTag = False
		self._tagStack  = []
		self._finished  = False

		# Options
		self._printsStack = False
		self._ignoreWS   = True
		self._endingTag  = 'html'

		# Handle optional args
		if emptyTags is not None:
			self.setEmptyTags(emptyTags)
		else:
			self.setEmptyTags(DefaultEmptyTags)
		if extraEmptyTags is not None:
			self.extendEmptyTags(extraEmptyTags)


	## Reading ##

	def readFileNamed(self, filename, retainRootTag=True):
		"""
		Reads the given file. Relies on readString(). See that method for more
		information.
		"""
		self._filename = filename
		contents = open(filename).read()
		return self.readString(contents, retainRootTag)

	def readString(self, string, retainRootTag=True):
		"""
		Reads the given string, storing the results and returning the root tag. You
		could continue to use HTMLReader object or disregard it and simply use the root
		tag.
		"""
		self._rootTag  = None
		self._tagStack = []
		self._finished = False
		self.reset()
		self._lineNumber = 1
		self.computeTagContainmentConfig()
		try:
			for line in string.split('\n'):
				self.feed(line + '\n')
				self._lineNumber += 1
			self.close()
		finally:
			self.reset()
		if retainRootTag:
			return self._rootTag
		else:
			tag = self._rootTag
			self._rootTag = None
			return tag


	## Printing ##

	def pprint(self, out=None):
		"""
		Pretty prints the tag, its attributes and all its children.
		Indentation is used for subtags.
		Print 'Empty.' if there is no root tag.
		"""
		if self._rootTag:
			self._rootTag.pprint(out)
		else:
			if out is None:
				out = sys.stdout
			out.write('Empty.')


	## Access ##

	def rootTag(self):
		"""
		Returns the root tag. May return None if no HTML has been read yet, or if the
		last invocation of one of the read methods was passed retainRootTag=False.
		"""
		return self._rootTag

	def filename(self):
		"""
		Returns the filename that was read, or None if no file was processed.
		"""
		return self._filename

	def emptyTags(self):
		"""
		Returns a list of empty tags. See also: class docs and setEmptyTags().
		"""
		return self._emptyTagList

	def setEmptyTags(self, tagList):
		"""
		Sets the HTML tags that are considered empty such as <br> and <hr>.
		The default is found in the global, DefaultEmptyTags, and is fairly thorough,
		but does not include <p>, <li> and some other tags that HTML authors often use
		as empty tags.
		"""
		self._emptyTagList = list(tagList)
		self._updateEmptyTagDict()

	def extendEmptyTags(self, tagList):
		"""
		Extends the current list of empty tags with the given list.
		"""
		self._emptyTagList.extend(tagList)
		self._updateEmptyTagDict()


	## Debugging ##

	def printsStack(self):
		return self._printsStack

	def setPrintsStack(self, flag):
		"""
		Sets the boolean value of the "prints stack" option. This is a debugging
		option which will print the internal tag stack during HTML processing. The
		default value is False.
		"""
		self._printsStack = flag


	## Command line ##

	def main(self, args=None):
		"""
		The command line equivalent of readFileNamed().
		Invoked when HTMLTag is run as a program.
		"""
		if args is None:
			args = sys.argv
		if len(args) < 2:
			self.usage()
		return self.readFileNamed(args[1])

	def usage(self):
		print 'HTMLTag: usage:  HTMLTag <html file>'
		sys.exit(1)


	## SGMLParser handlers ##

	def handle_data(self, data):
		if self._finished:
			return
		assert type(data) is StringType
		if self._ignoreWS:
			data = data.strip()
			if not data:
				return
		if self._tagStack:
			self._tagStack[-1].addChild(data)
		else:
			print '<> data=%r' % repr(data)


	def handle_pi(self, data):
		raise HTMLTagProcessingInstructionError, 'Was not expecting a processing instruction: %r' % data

	def unknown_starttag(self, name, attrs):
		if self._finished:
			return
		tag = HTMLTag(name, lineNumber=self._lineNumber)
		for attrName, value in attrs:
			tag.readAttr(attrName, value)
		if self._emptyTagDict.has_key(name):
			# We'll never have any children. Boo hoo.
			assert self._rootTag, 'Cannot start HTML with an empty tag: %r' % tag
			self._tagStack[-1].addChild(tag)
			empty = True
		else:
			# We could have children, so we go on the stack
			# Also, if this is the first tag, then make it the root.
			# If it's the first tag and it isn't an <html> tag,
			# create a fake "container" html tag.
			if self._tagStack:
				lastTag = self._tagStack[-1]
				# is this legal?
				tagConfig = self._tagContainmentConfig.get(lastTag.name())
				if tagConfig:
					tagConfig.encounteredTag(name, self._lineNumber)
				# tell last tag about his new child
				lastTag.addChild(tag)
			elif name != 'html' and self._fakeRootTagIfNeeded:
				self._rootTag = HTMLTag('html')
				self._tagStack.append(self._rootTag)
				self._tagStack[-1].addChild(tag)
				self._usedFakeRootTag = True
			else:
				self._rootTag = tag
			self._tagStack.append(tag)
			empty = False
		if self._printsStack:
			prefix = ('START', '-----')[empty]
			print '%s %s: %r' % (prefix, name.ljust(6), self._tagStack)

	def unknown_endtag(self, name):
		if self._finished:
			return
		if name == self._endingTag:
			self._finished = True
		openingTag = self._tagStack.pop()
		if self._printsStack:
			print 'END   %s: %r' % (name.ljust(6), self._tagStack)
		if openingTag.name() != name:
			raise HTMLTagUnbalancedError('line %i: opening is %r, but closing is <%s>.' % \
				(self._lineNumber, openingTag, name), line=self._lineNumber, opening=openingTag.name(), closing=name, tagStack=self._tagStack)
		else:
			openingTag.closedBy(name, self._lineNumber)

	def close(self):
		if len(self._tagStack) > 0 and not (len(self._tagStack) == 1 and self._usedFakeRootTag):
			raise HTMLTagIncompleteError('line %i: tagStack = %r' % (self._lineNumber, self._tagStack), line=self._lineNumber, tagStack=repr(self._tagStack))
		SGMLParser.close(self)


	## Self utility ##

	def _updateEmptyTagDict(self):
		"""Create a dictionary out of the empty tag list for quick look up."""
		dict = {}
		for tag in self._emptyTagList:
			dict[tag] = None
		self._emptyTagDict = dict

	# The following dict defines for various tags either:
	#    + the complete set of tags that can be contained within
	#    - a set of tags that cannot be contained within
	# This information helps HTMLReader detect some types of errors
	# earlier and other types of errors, it would never detect.
	tagContainmentConfig = {
		'html':   'canOnlyHave head body',
		'head':   'cannotHave  html head body',
		'body':   'cannotHave  html head body',
		'table':  'canOnlyHave tr thead tbody tfoot a',
		# a because in IE you can wrap a row in <a> to make the entire row clickable
		'tr':     'canOnlyHave th td',
		'td':     'cannotHave  td tr',
		'select': 'canOnlyHave option',
	}

	def computeTagContainmentConfig(self):
		config = {}
		for key, value in self.tagContainmentConfig.items():
			if isinstance(value, StringType):
				value = value.split()
				configClass = configClassForName.get(value[0])
				if configClass is None:
					raise KeyError, 'Unknown config name %r for value %r in %s.tagContainmentConfig' % (key, value, self.__class__.__name__)
				config[key] = configClass(key, value[1:])
			else:
				assert isinstance(value, TagConfig), 'key=%r, value=%r' % (key, value)
				config[key] = value
		self._tagContainmentConfig = config


	## Optimizations ##

	if runFast:
		finish_starttag = unknown_starttag
		finish_endtag = unknown_endtag


class TagConfig:

	def __init__(self, name, tags):
		self.name = name
		# turn list of tags into a dict/set for fast lookup (avoid linear searches)
		dict = {}
		for tag in tags:
			dict[tag] = None
		self.tags = dict

	def encounteredTag(self, tag, lineNum):
		raise SubclassResponsiblityError, self.__class__


class TagCanOnlyHaveConfig(TagConfig):

	def encounteredTag(self, tag, lineNum):
		if not self.tags.has_key(tag.lower()):
			raise HTMLNotAllowedError('line %i: the tag %r is not allowed in %r which can only have %r.' % (
				lineNum, tag, self.name, self.tags.keys()), line=lineNum, encounteredTag=tag, containingTag=self.name, canOnlyHave=self.tags.keys())


class TagCannotHaveConfig(TagConfig):

	def encounteredTag(self, tag, lineNum):
		if self.tags.has_key(tag.lower()):
			raise HTMLNotAllowedError('line %i: The tag %r is not allowed in %r which cannot have %r.' % (
				lineNum, tag, self.name, self.tags.keys()), line=lineNum, enounteredTag=tag, containingTag=self.name, cannotHave=self.tags.keys())


configClassForName = {
	'canOnlyHave':   TagCanOnlyHaveConfig,
	'cannotHave': TagCannotHaveConfig,
}


if __name__ == '__main__':
	html = HTMLReader().main()
	html.pprint()
