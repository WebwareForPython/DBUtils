"""MixIns

This file contains "mix-in" classes that are mixed in with classes
found in MiddleKit.Core and .Run. The mix-ins are named directly
after their target classes, which is how they get bound in InstallMixIns().

The InstallMixIns() functions is called from this module.
So all you need do is import this module to make the mix-ins take effect.
This is done in __init__.py.

If you add another mix-in then update the list of names found
in InstallMixIns().

"""

from types import LongType
from WebUtils.Funcs import htmlEncode


def splitWords(s):
	res = []
	for c in s:
		if c.upper() == c:
			res.append(' ')
			res.append(c.lower())
		else:
			res.append(c)
	return ''.join(res)


class ObjectStore:

	def htObjectsOfClassNamed(self, className):
		objs = self.fetchObjectsOfClass(className)
		return self.htObjectsInList(objs, className)

	def htObjectsInList(self, objs, adjective):
		"""Get HTML for list of onjects.

		Returns an HTML string for a list of MiddleKit objects
		and their attributes. The adjective describes the type
		of objects and is used in the output (for example 'Customer').
		This is a utility method for use by anyone.

		"""
		if objs is None:
			objs = []
		ht = []
		suffix = ('s', '')[len(objs) == 1]
		ht.append('<span class="TablePrefix">%i %s object%s</span>'
			% (len(objs), adjective, suffix))
		ht.append('<table border="1" cellspacing="0" cellpadding="2"'
			' class="ObjectsTable">')
		if objs:
			klass = objs[0].klass()
			ht.append(klass.htHeadingsRow())
			for obj in objs:
				newKlass = obj.klass()
				if newKlass != klass:
					# If we hit a new class, write new headings
					klass = newKlass
					ht.append(klass.htHeadingsRow())
				ht.append(obj.htAttrsRow())
		else:
			ht.append('<tr><td class="NoObjectsCell">'
				'No %s objects.</td></tr>' % adjective)
		ht.append('</table>\n')
		return ''.join(ht)


class Klass:

	def htHeadingsRow(self):
		ht = ['<tr>']
		ht.append('<th class="TableHeading">class</th>')
		ht.append('<th class="TableHeading">serial</th>')
		for attr in self.allAttrs():
			heading = splitWords(attr.name())
			ht.append('<th class="TableHeading">%s</th>' % heading)
		ht.append('</tr>\n')
		return ''.join(ht)


class MiddleObject:

	def htAttrsRow(self):
		ht = ['<tr>']
		ht.append('<td class="TableData">%s</td>' % self.__class__.__name__)
		ht.append('<td class="TableData">%i</td>' % self.serialNum())
		for attr in self.klass().allAttrs():
			value = getattr(self, '_'+attr.name())
			ht.append('<td class="TableData">%s</td>'
				% attr.htValue(value, self))
		ht.append('</tr>\n')
		return ''.join(ht)

	def htObjectsInList(self, listName, coalesce=1):
		list = self.valueForKey(listName)
		# We coalesce the classes together and present in alphabetical order
		if list is not None and coalesce:
			klasses = {}
			for obj in list:
				klassName = obj.klass().name()
				if klasses.has_key(klassName):
					klasses[klassName].append(obj)
				else:
					klasses[klassName] = [obj]
			klassNames = klasses.keys()
			klassNames.sort()
			list = []
			for name in klassNames:
				list.extend(klasses[name])
		return self.store().htObjectsInList(list, listName)


class Attr:

	def htValue(self, value, obj):
		return htmlEncode(str(value))


class ObjRefAttr:

	def htValue(self, value, obj):
		if type(value) is LongType:
			classSerialNum = (value & 0xFFFFFFFF00000000L) >> 32
			objSerialNum = value & 0xFFFFFFFFL
			klass = obj.store().klassForId(classSerialNum)
			klassName = klass.name()
			return '<a href="BrowseObject?class=%s&serialNum=%i">%s.%i</a>' \
				% (klassName, objSerialNum, klassName, objSerialNum)
		else:
			return htmlEncode(str(value))


class ListAttr:

	def htValue(self, value, obj):
		if value is None:
			return '<a href="BrowseList?class=%s&serialNum=%i&attr=%s">list' \
				'</a>' % (obj.klass().name(), obj.serialNum(), self.name())


def InstallMixIns():
	from MiscUtils.MixIn import MixIn

	theGlobals = globals()
	names = 'ObjectStore Klass MiddleObject Attr ObjRefAttr ListAttr'.split()
	places = 'Core Run'.split()
	for name in names:
		mixed = 0
		for place in places:
			nameSpace = {}
			try:
				exec 'from MiddleKit.%s.%s import %s' \
					% (place, name, name) in nameSpace
			except ImportError:
				pass
			else:
				pyClass = nameSpace[name]
				mixIn = theGlobals[name]
				MixIn(pyClass, mixIn)
				mixed = 1
				continue
		assert mixed, 'Could not mix-in %s.' % name


InstallMixIns()
