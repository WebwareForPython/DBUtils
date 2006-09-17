def test(store):
	"""
	Bug discovered by Chuck Esterbrook on 2002-10-29.
	"""
	from Bar import Bar
	from Qux import Qux

#	import sys; store._sqlEcho = sys.stdout

	# Since we're the second empty test, double check that the db is really empty
	assert len(store.fetchObjectsOfClass(Bar))==0
	assert len(store.fetchObjectsOfClass(Qux))==0

	qux = Qux()
	store.addObject(qux)
	bar = Bar()
	qux.setBar(bar)
	store.addObject(bar)

	store.saveChanges()
	quxes = store.fetchObjectsOfClass(Qux)
	assert len(quxes)==1
	qux2 = quxes[0]
	assert qux2 is qux
	assert qux.bar() is not None  # the sign of the bug in question
	assert qux.bar() is bar  # what we should expect

	store.clear()
	qux = store.fetchObjectsOfClass(Qux)[0]
	assert qux.bar() is not None
