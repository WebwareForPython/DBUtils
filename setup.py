"""Setup Script for DBUtils"""

import warnings
from distutils.core import setup
from sys import version_info

py_version = version_info[:2]
if not (2, 6) <= py_version <= (2, 7) and not (3, 4) <= py_version < (4, 0):
    raise ImportError('Python %d.%d is not supported by DBUtils.' % py_version)

warnings.filterwarnings('ignore', 'Unknown distribution option')

__version__ = '1.3'

readme = open('README.md').read()

setup(
    name='DBUtils',
    version=__version__,
    description='Database connections for multi-threaded environments.',
    long_description=readme,
    long_description_content_type='text/markdown',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
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
