def test(store):
	"""
	Bug report from Stefan Karlsson <stefan@everynet.se> on Dec 3 2001.
	Obj refs can be incorrectly stored to the database as zeroes for newly created objects.
	"""

	from Bar import Bar
	from Foo import Foo
	from BarReq import BarReq

	# Since we're the second empty test, double check that the db is really empty
	assert len(store.fetchObjectsOfClass(Bar))==0
	assert len(store.fetchObjectsOfClass(Foo))==0

	bar = Bar()
	foo = Foo()
	store.addObject(bar)
	store.addObject(foo)
	bar.setFoo(foo)

	store.saveChanges()

	bars = store.fetchObjectsOfClass(Bar)
	assert len(bars)==1
	bar2 = bars[0]
	assert bar2 is bar
	assert bar.foo() is not None  # the sign of the bug in question
	assert bar.foo() is foo  # what we should expect

	store.clear()
	bar = store.fetchObjectsOfClass(Bar)[0]
	assert bar.foo() is not None
