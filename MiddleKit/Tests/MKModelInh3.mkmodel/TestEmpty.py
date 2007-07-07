def test(store):
	from Foo import Foo
	from MiscUtils.DataTable import DataTable

	thing = store.model().klass('Thing')
	assert thing.hasAttr('a')
	assert thing.hasAttr('b')
	assert not thing.hasAttr('i')

	f = Foo()
	f.setA('a')
	f.setB('b')
	f.setX(1)

	store.addObject(f)
	store.saveChanges()

	store.clear()
	f = store.fetchObjectsOfClass('Foo')[0]
	assert f.a() == 'a'
	assert f.b() == 'b'
	assert f.x() == 1
