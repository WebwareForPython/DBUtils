"""
FUTURE

* Parameterize the database and everything else.
  Currently hard coded to pgdb template1 database.

* We don't really test performance here.
  E.g., we don't do benchmarks to see if DBPool actually helps or not.

"""


import sys
sys.path.insert(1, '..')
from DBPool import DBPool


def Test(iterations=15):
	try:
		dbapi_name = 'pgdb'
		dbapi = __import__(dbapi_name)
		pool = DBPool(dbapi, 10, database='template1')
		for i in range(iterations):
			db = pool.connection()
			cursor = db.cursor()
			cursor.execute("select datname from pg_database order by 1")
			r = cursor.fetchmany(5)
			r = ', '.join(map(lambda s: s[0], r))
			print i, r
			db.close()
	except:
		import traceback
		traceback.print_exc()
		print 'You need the pgdb adapter and a test database for this example.'


if __name__ == '__main__':
	Test()
