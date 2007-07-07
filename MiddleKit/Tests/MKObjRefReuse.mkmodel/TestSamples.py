from MiddleKit.Run.MiddleObject import MiddleObject


def assertBazIsObjRef(bar):
	bazAttr = getattr(bar, '_baz')
	assert isinstance(bazAttr, MiddleObject), \
		'bazAttr=%r, type(bazAttr)=%r' % (bazAttr, type(bazAttr))

def test(store):
	foos = store.fetchObjectsOfClass('Foo')
	assert len(foos) == 2
	foo1 = foos[0]
	foo2 = foos[1]

	bar = foo1.bar()
	baz = foo1.bar().baz()
	assert baz.x() == 5 # just to make sure we got what we expected
	assertBazIsObjRef(bar)

	# Now here's what we're really testing for:
	#
	# When we ask foo2 for bar(), it's baz attribute
	# should still be a Python pointer, NOT a longint
	# (e.g., unpacked obj ref)
	#
	# This was not the case earlier, because store.fetchObject()
	# was _always_ calling store.fetchObjectsOfClass() instead of
	# checking the in-memory object cache first.

	bar = foo2.bar()
	assertBazIsObjRef(bar)
	if 0:
		bazAttr = getattr(bar, '_baz')
		assert isinstance(bazAttr, MiddleObject), \
			'bazAttr=%r, type(bazAttr)=%r' % (bazAttr, type(bazAttr))
