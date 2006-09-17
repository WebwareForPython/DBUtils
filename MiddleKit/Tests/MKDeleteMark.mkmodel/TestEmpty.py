from Foo import Foo
from Bar import Bar
from MiddleKit.Run import ObjectStore
import A, B, C, D, E, F, G, H, I, J, K, L

def test(store):

	testOther(store, A.A, DELETE_REFERENCED_ERROR)
	testOther(store, B.B, DELETE_REFERENCED_ERROR)
	testOther(store, C.C, DELETE_FOO)
	testOther(store, D.D, DELETE_FOO_AND_OBJECT)

	print '*** passed testOther'

	testSelf(store, E.E, DELETE_OBJECT)
	testSelf(store, F.F, DELETE_OBJECT_WITH_REFERENCES_ERROR)
	testSelf(store, G.G, DELETE_OBJECT)
	testSelf(store, H.H, DELETE_FOO_AND_OBJECT)

	print '*** passed testSelf'

	testSelfList(store, I.I, DELETE_FOO)
	testSelfList(store, J.J, DELETE_OBJECT_WITH_REFERENCES_ERROR)
	testSelfList(store, K.K, DELETE_FOO)
	testSelfList(store, L.L, DELETE_FOO_AND_OBJECT)

	print '*** passed testSelfList'

# These are possible values for expectedResult
DELETE_FOO = 1
DELETE_OBJECT = 2
DELETE_FOO_AND_OBJECT = 3
DELETE_REFERENCED_ERROR = 4
DELETE_OBJECT_WITH_REFERENCES_ERROR = 5

def testOther(store, klass, expectedResult):
	"""
	Test creating an instance of a specified class, that points to an instance of Foo,
	which itself points to an instance of Bar.  Then try to delete the Foo, and
	make sure that the expected result happens.
	"""
	# Run the test, deleting the specified object and verifying the expected result
	object, foo, bar = setupTest(store, klass)
	try:
		runTest(store, klass, foo, expectedResult)
	finally:
		cleanupTest(store, klass)

def testSelf(store, klass, expectedResult):
	"""
	Test creating an instance of a specified class, that points to an instance of Foo,
	which itself points to an instance of Bar.  Then try to delete the object of
	the specified class, and make sure that the expected result happens.
	"""
	# Run the test, deleting the specified object and verifying the expected result
	object, foo, bar = setupTest(store, klass)
	try:
		runTest(store, klass, object, expectedResult)
	finally:
		cleanupTest(store, klass)

def testSelfList(store, klass, expectedResult):
	"""
	Test creating an instance of a specified class, pointed to by the list attribute in
	an instance of Foo, which itself points to an instance of Bar.  Then try to delete the Foo,
	and make sure that the expected result happens.
	"""
	# Run the test, deleting the specified object and verifying the expected result
	object, foo, bar = setupListTest(store, klass)
	try:
		runTest(store, klass, foo, expectedResult)
	finally:
		cleanupTest(store, klass)

def setupTest(store, klass):
	"""
	Setup 3 objects: one of the specified klass, pointing to a Foo, pointing to a Bar.
	Returns tuple (object of specified klass, foo, bar).
	"""
	# Create a Foo and a Bar, with the Foo pointing to the Bar
	bar = Bar()
	bar.setX(42)
	foo = Foo()
	foo.setBar(bar)
	store.addObject(foo)
	store.addObject(bar)
	store.saveChanges()

	# create an instance of klass pointing to Foo
	object = klass()
	object.setFoo(foo)
	store.addObject(object)
	store.saveChanges()

	return object, foo, bar

def setupListTest(store, klass):
	"""
	Setup 3 objects: one of the specified klass, pointing to a Foo, pointing to a Bar.
	Returns tuple (object of specified klass, foo, bar).
	"""
	# Create a Foo and a Bar, with the Foo pointing to the Bar
	bar = Bar()
	bar.setX(42)
	foo = Foo()
	foo.setBar(bar)
	store.addObject(foo)
	store.addObject(bar)
	store.saveChanges()

	# create an instance of klass and put it into the list in foo
	object = klass()
	getattr(foo, 'addToListOf%s' % klass.__name__)(object)
	store.saveChanges()

	return object, foo, bar

def runTest(store, klass, objectToDelete, expectedResult):
	# Try to delete the specified object, then check that the expected result is what happened
	try:
		store.deleteObject(objectToDelete)
		store.saveChanges()
	except ObjectStore.DeleteReferencedError:
		assert expectedResult == DELETE_REFERENCED_ERROR
		objects = store.fetchObjectsOfClass(klass)
		foos = store.fetchObjectsOfClass(Foo)
		assert len(objects) == 1
		assert len(foos) == 1
	except ObjectStore.DeleteObjectWithReferencesError:
		assert expectedResult == DELETE_OBJECT_WITH_REFERENCES_ERROR
		objects = store.fetchObjectsOfClass(klass)
		foos = store.fetchObjectsOfClass(Foo)
		assert len(objects) == 1
		assert len(foos) == 1
	else:
		objects = store.fetchObjectsOfClass(klass)
		foos = store.fetchObjectsOfClass(Foo)
		if expectedResult == DELETE_FOO:
			assert len(objects) == 1
			assert objects[0].foo() == None
			assert len(foos) == 0
		elif expectedResult == DELETE_OBJECT:
			assert len(objects) == 0
			assert len(foos) == 1
		elif expectedResult == DELETE_FOO_AND_OBJECT:
			assert len(objects) == 0
			assert len(foos) == 0
		else:
			raise AssertionError, 'unknown expectedResult value'
	bars = store.fetchObjectsOfClass(Bar)
	assert len(bars) == 1

def cleanupTest(store, klass):
	# Clean out all leftover objects
	store.clear()
	store.executeSQL('delete from Foo;')
	store.executeSQL('delete from Bar;')
	store.executeSQL('delete from %s;' % klass.__name__)
	print
