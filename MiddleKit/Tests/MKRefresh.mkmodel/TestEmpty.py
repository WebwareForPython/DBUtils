def test(store):
	from Book import Book

	b = Book()
	b.setTitle('foo')
	store.addObject(b)
	store.saveChanges()
	serialNum = b.serialNum()

	b = store.fetchObject(Book, serialNum)
	b.setTitle('bar')
	try:
		b = store.fetchObject(Book, serialNum)
	except AssertionError:
		# an assertion _should_ be generated, because we are attempting 
		# to refresh a modified object.
		pass
	else:
		assert 0, 'Should have got an assertion failure, but none was raised.'
