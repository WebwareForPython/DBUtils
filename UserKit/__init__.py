# UserKit
# Webware for Python


def InstallInWebKit(appServer):
	pass


def dont_use_combineManagerClasses(*classesOrNamesThereof):
	"""
	----
	While this was a nice idea that nearly worked, it broke on keyword arguments to __init__ methods. Fixing it seemed nastier than the next solution: Split RoleUserManager's methods out into RoleUserManagerMixIn, which inherits nothing. Then use the mix-in for the various manager classes, taking care of problems manually in the classes.
	@@ 2002-04-10 ce
	----

	Given a list of "orthogonal" classes (or their names), that all inherit from UserManager, this function returns a new class that combines all of them. By "orthogonal" we mean that the features of the user manager are separate concerns and not dependent on each other.
	Out of the box, UserKit provides custom user managers for:
		* persistence
		* defining roles

	Example:
		from UserKit.UserManagerToFile import UserManagerToFile as UMFile
		from UserKit.RoleUserManager import RoleUserManager as UMRole
		MyUserManager = UserManagerCombo(UMFile, UMRole)

	Or using strings:
		MyUserManager = UserManagerCombo('UserManagerToFile', 'RoleUserManager')

	Note that strings only work for UserManager subclasses found in UserKit (or somewhere on the Python path). @@ 2001-04-03 ce: a future version should accepted dotted notation for pkgA.pkgB.module.

	Do not include the top level, abstract UserManager class in the list.

	If you must know, the classes are combined by stacking copies of them vertically. The original classes are not modified in any way.

	You could pass a single parameter if you wanted.

	For subclassers of UserManager: In order to qualify for use by this class you have to follow some conventions:
		- Suppose your class name is Foo
		- Your class must inherit UserKit.UserManager
		- Your class must define this attribute:
			baseOfFoo = UserManager
		- When "invoking super" you cannot do this:
			UserManager.someMethod(self, arg1, arg2)
		  But instead must do this:
			self.baseOfFoo.someMethod(self, arg1, arg2)
	Yes, that's a little weird. But it's minimal and it empowers this function to create a combination class from orthogonal subclasses of UserManager. I think that if Python had a true "super" feature like Smalltalk and Objective-C, these conventions wouldn't be necessary.
	"""
	import types

	classes = []
	for arg in classesOrNamesThereof:
		if type(arg) is types.StringType:
			module = __import__(arg, globals())
			pyClass = getattr(module, arg, None)
			assert pyClass is not None
			arg = pyClass
		assert type(arg) is types.ClassType
		classes.append(arg)

	from UserManager import UserManager
	assert UserManager not in classes, 'You cannot specify the abstract ancestor class, UserManager, as one of the classes to combine. It is implicit.'

	# Stack the classes in reverse order.
	# I'm not sure why; just feels right.
	# Theoretically, it shouldn't matter since the classes
	# are supposed to be orthogonal.
	classes.reverse()
	classes.append(UserManager)

	theClass = None
	prevClass = None
	for curClass in classes:
		#print '>> curClass = %r, %r' % (curClass, type(curClass))
		if prevClass:
			class NewClass: pass
			NewClass.__name__ = prevClass.__name__
			NewClass.__dict__.update(prevClass.__dict__)
			NewClass.__bases__ = (curClass,)
			baseOfName = 'baseOf' + prevClass.__name__
			setattr(NewClass, baseOfName, curClass)
			if theClass is None:
				theClass = NewClass
		prevClass = curClass

	assert issubclass(theClass, UserManager)
	theClass.__name__ = '_'.join([c.__name__ for c in classes])

	if 0:
		# For debugging
		print
		print '>> UserKit.combineUserManagers()'
		c = theClass
		num = 1
		while c is not None:
			print '%02i. c = %s' % (num, c)
			print 'c.__bases__ =', c.__bases__
			for attrName in dir(c):
				if attrName.startswith('baseOf'):
					print 'c.%s = %s' % (attrName, getattr(c, attrName))
			print
			if not c.__bases__:
				break
			c = c.__bases__[0]
			num += 1
		print
		print


	return theClass
