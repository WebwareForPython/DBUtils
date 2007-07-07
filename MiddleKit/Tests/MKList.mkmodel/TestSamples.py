def test(store):
	from Foo import Foo
	from Bar import Bar

	foos = store.fetchObjectsOfClass(Foo)
	assert len(foos) == 2
	f1, f2 = foos
	assert len(f1.bars()) == 2, 'bars=%r' % f1.bars()
	assert len(f2.bars()) == 3