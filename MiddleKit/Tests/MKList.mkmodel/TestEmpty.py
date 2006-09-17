from Foo import Foo
from Bar import Bar
from types import *


def reset(store):
	store.clear()
	store.executeSQL('delete from Foo;')
	store.executeSQL('delete from Bar;')

def testAddToBars(store):
	# Test 1: Use addToBars()
	f = Foo()
	store.addObject(f)

	b = Bar()
	f.addToBars(b)
	b.dumpAttrs()
	store.saveChanges()

	store.clear()
	f = store.fetchObjectsOfClass(Foo)[0]
	bars = f.bars()
	assert len(bars)==1, 'bars=%r' % bars
	assert bars[0].foo()==f
	reset(store)

def test(store):
	# We invoke testAddToBars twice on purpose, just to see that
	# the second time around, things are stable enough to pass again
	testAddToBars(store)
	testAddToBars(store)

	# Test 2: do not use addToBars()
	# @@ 2001-02-11 ce: this is probably not a valid test in the long run
	f = Foo()
	f.setX(0) # @@ 2000-11-25 ce: take out after fixing default value bug in gen py code
	store.addObject(f)
	b = Bar()
	b.setFoo(f)
	b.setX(7)
	store.addObject(b)
	store.saveChanges()
	store.clear()

	f = store.fetchObjectsOfClass(Foo)[0]
	assert f._mk_store
	assert f._mk_inStore
	bars = f.bars()
	assert type(bars) is ListType
	assert len(bars)==1, 'bars=%r' % bars
	assert bars[0].x()==7

	# Test addToXYZ() method
	bar = Bar()
	bar.setX(7)
	f.addToBars(bar)
	assert bar.foo()==f
	store.saveChanges()
	store.clear()

	f = store.fetchObjectsOfClass(Foo)[0]
	bars = f.bars()
	assert type(bars) is ListType
	assert len(bars)==2, 'bars=%r' % bars
	assert bars[0].x()==7
	assert bars[1].x()==7

	# Test the assertion checking in addToXYZ()
	try:		f.addToBars(None)
	except:		pass
	else:		NoException('f.addToBars(None) # None not allowed')

	try:		f.addToBars(5)
	except:		pass
	else:		NoException('f.addToBars(5) # not an object')

	try:		f.addToBars(f)
	except:		pass
	else:		NoException('f.addToBars(f) # wrong class')

	try:		f.addToBars(bar)
	except:		pass
	else:		NoException('f.addToBars(bar) # already added')


def NoException(codeString):
	raise Exception, 'Failed to raise exception for: ' + codeString
