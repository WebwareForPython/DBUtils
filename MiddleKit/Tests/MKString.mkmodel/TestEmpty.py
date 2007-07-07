def test(store):
	from Foo import Foo

	a100 = 'a'*100
	b500 = 'b'*500
	c70000 = 'c'*70000

	f = Foo()
	f.setMax100(a100)
	f.setMax500(b500)
	f.setMax70000(c70000)
	store.addObject(f)
	store.saveChanges()

	store.clear()
	results = store.fetchObjectsOfClass(Foo)
	f = results[0]
	assert f.max100() == a100
	assert f.max500() == b500
	assert f.max70000() == c70000

	difficultString = ''.join([chr(i) for i in range(1, 256)])
	f = Foo()
	f.setMax500(difficultString)
	store.addObject(f)
	store.saveChanges()
	serialNum = f.serialNum()
	store.clear()
	result = store.fetchObject(Foo, serialNum)
	assert result.max500() == difficultString

