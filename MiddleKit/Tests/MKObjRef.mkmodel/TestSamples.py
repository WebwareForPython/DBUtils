def test(store):
	from Foo import Foo
	from Bar import Bar

	bar = store.fetchObjectsOfClass(Bar)[0]
	store.dumpKlassIds()
	assert bar.foo().x() == 1

	foo = store.fetchObjectsOfClass(Foo)[0]
	assert foo == bar.foo()
