def test(store):
	from Foo import Foo

	f = Foo()
	f.setE('red')
	f.setE('green')
	store.addObject(f)
	store.saveChanges()

	results = store.fetchObjectsOfClass(Foo)
	assert len(results)==1, 'len=%s, results=%s' % (len(results), results)

	assert f.e()=='green' or f.e()==1, f.e()

	f = None
	store.clear()

	results = store.fetchObjectsOfClass(Foo)
	assert len(results)==1, 'len=%s, results=%s' % (len(results), results)
	f = results[0]

	assert f.e()=='green' or f.e()==1, f.e()

	f.setE(None)
	store.saveChanges()

	f = None
	store.clear()
	f = store.fetchObjectsOfClass(Foo)[0]
	assert f.e() is None, f.e()

	try:
		f.setE('wrong')
	except ValueError:
		pass
	except:
		assert 0, 'expecting a ValueError for invalid enums'
	else:
		assert 0, 'expecting a ValueError for invalid enums'
