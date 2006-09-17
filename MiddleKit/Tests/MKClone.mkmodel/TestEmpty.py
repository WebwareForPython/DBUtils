def test(store):
	from Book import Book
	from Author import Author
	from Loan import Loan
	from Wrote import Wrote
	from Shelf import Shelf

	classics = Shelf()
	classics.setName('Classics')
	store.addObject(classics)
	store.saveChanges()
	
	ed = Author()
	ed.setName('Edmund Wells')

	david = Book()

	wrote = Wrote()
	ed.addToWrote(wrote)
	david.addToAuthors(wrote)
	david.setTitle('David Coperfield')
	david.setPublisher('Monty Python')

	loan = Loan()
	loan.setBorrower('A. Git')
	david.addToLoans(loan)
	david.setShelf(classics)

	store.addObject(david)
	store.saveChanges()

	# create a clone of the book and associated objects
	grate = david.clone()
	grate.setTitle('Grate Expections')
	store.addObject(grate)
	store.saveChanges()

	assert david is not grate
	assert len(grate.authors()) == 1
	assert david.authors()[0] is not grate.authors()[0]  
	assert grate.authors()[0].author() is ed
	assert len(grate.loans()) == 0
	assert grate.shelf() is david.shelf()
	assert grate.publisher() == 'Monty Python'
