"""Setup Script for DBUtils"""

from sys import version_info

__version__ = '1.2'

py_version = version_info[:2]
if py_version < (2, 6):
    raise ImportError('Python %d.%d is not supported by DBUtils.' % py_version)

import warnings
warnings.filterwarnings('ignore', 'Unknown distribution option')

from distutils.core import setup

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
    classifiers=['Development Status :: 5 - Production/Stable',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.0',
        'Programming Language :: Python :: 3.1',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Topic :: Database',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ],
    author='Christoph Zwerschke',
    author_email='cito@online.de',
    url='https://cito.github.io/DBUtils/',
    platforms=['any'],
    license='MIT License',
    packages=['DBUtils', 'DBUtils.Examples', 'DBUtils.Tests'],
    package_data={'DBUtils': ['Docs/*']}
)
