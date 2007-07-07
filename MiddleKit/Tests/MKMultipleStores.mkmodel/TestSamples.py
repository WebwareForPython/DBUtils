def test(store):
	from Thing import Thing

	things = store.fetchObjectsOfClass('Thing')
	assert len(things) > 1 # make sure have at least some data to work with
	for thing in things:
		assert thing.store() == store

	dbArgs = store._dbArgs
	newStore = store.__class__(**dbArgs)
	newStore.setModel(store.model())
	assert newStore != store  # paranoia

	things = newStore.fetchObjectsOfClass('Thing')
	assert len(things) > 1
	for thing in things:
		assert thing.store() == newStore


	# and now for an entirely different store
	import os, sys
	sys.path.insert(1, os.path.abspath(os.pardir))
	try:
		from TestDesign import test as generate
		model = generate('../MKBasic.mkmodel', configFilename=None, workDir='WorkDir2') # toTestDir='../../',

		diffStore = store.__class__(**dbArgs)
		diffStore.setModel(model)
		assert diffStore.model() is model
		personClass = model.klass('Person').pyClass()
		person = personClass()
		person.setFirstName('Chuck')
		assert person.firstName() == 'Chuck'
		diffStore.addObject(person)
		assert person.store() is diffStore, 'store=%r' % person.store()
		diffStore.saveChanges()
		assert person.store() is diffStore, 'store=%r' % person.store()
		assert diffStore is not newStore

		from TestCommon import rmdir
		rmdir('WorkDir2')
	finally:
		del sys.path[1]
