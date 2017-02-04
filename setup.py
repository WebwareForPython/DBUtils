"""Setup Script for DBUtils"""

__version__ = '1.1.1'

from sys import version_info

py_version = version_info[:2]
if not (2, 3) <= py_version < (3, 0):
    raise ImportError('Python %d.%d is not supported by DBUtils.' % py_version)

import warnings
warnings.filterwarnings('ignore', 'Unknown distribution option')

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup
    try:
        from distutils.dist import DistributionMetadata
    except ImportError:
        pass
    else:
        try:
            DistributionMetadata.classifiers
        except AttributeError:
            DistributionMetadata.classifiers = None
        try:
            DistributionMetadata.package_data
        except AttributeError:
            DistributionMetadata.package_data = None
        try:
            DistributionMetadata.zip_safe
        except AttributeError:
            DistributionMetadata.zip_safe = None

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
        'Programming Language :: Python :: 2.3',
        'Programming Language :: Python :: 2.4',
        'Programming Language :: Python :: 2.5',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
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
    package_data={'DBUtils': ['Docs/*']},
    zip_safe=0
)
