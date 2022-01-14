"""Setup Script for DBUtils"""

import warnings
try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup
from sys import version_info

py_version = version_info[:2]
if not (3, 6) <= py_version < (4, 0):
    raise ImportError(
        'Python {}.{} is not supported by DBUtils.'.format(*py_version))

warnings.filterwarnings('ignore', 'Unknown distribution option')

__version__ = '3.0.2'

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
        'Topic :: Database',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Operating System :: OS Independent',
    ],
    author='Christoph Zwerschke',
    author_email='cito@online.de',
    url='https://webwareforpython.github.io/DBUtils/',
    download_url="https://pypi.org/project/DBUtils/",
    project_urls={
        'Documentation':
            'https://webwareforpython.github.io/DBUtils/main.html',
        'Changelog':
            'https://webwareforpython.github.io/DBUtils/changelog.html',
        'Issue Tracker':
            'https://github.com/WebwareForPython/DBUtils/issues',
        'Source Code':
            'https://github.com/WebwareForPython/DBUtils'},
    platforms=['any'],
    license='MIT License',
    packages=['dbutils']
)
