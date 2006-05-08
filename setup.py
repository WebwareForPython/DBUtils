from distutils.core import setup

import warnings
warnings.filterwarnings('ignore', 'Unknown distribution option')

import sys
# patch distutils if it can't cope with the "classifiers" keyword
if sys.version < '2.2.3':
	from distutils.dist import DistributionMetadata
	DistributionMetadata.classifiers = None
	DistributionMetadata.download_url = None

__version__ = '0.9.1'

setup(
	name='DBUtils',
	version=__version__,
	description='Database connections for multi-threaded environments.',
	long_description='''\
DBUtils is a suite of tools providing solid, persistent and pooled connections
to a database that can be used in all kinds of multi-threaded environments
like Webware for Python or other web application servers. The suite supports
DB-API 2 compliant database interfaces and the classic PyGreSQL interface.
''',
	classifiers=['Development Status :: 4 - Beta',
		'Environment :: Web Environment',
		'Intended Audience :: Developers',
		'License :: OSI Approved :: Open Software License',
		'Programming Language :: Python',
		'Topic :: Database',
		'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
		'Topic :: Software Development :: Libraries :: Python Modules'
	],
	author='Christoph Zwerschke',
	author_email='cito@online.de',
	url='http://www.webwareforpython.org/DBUtils',
	download_url='http://www.webwareforpython.org/downloads/DBUtils/',
	platforms=['any'],
	license='Open Software License',
	packages=['DBUtils', 'DBUtils.Examples', 'DBUtils.Testing'],
	package_data={'DBUtils': ['Docs/*']}
)
