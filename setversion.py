#!/usr/bin/env python

"""Set version.

This script sets the DBUtils version number information
consistently in all files of the distribution.

"""

# Version format is (Major, Minor, Sub, Alpha/Beta/etc)
# The Sub is optional, and if 0 is not returned.
# Examples: (0, 8, 1, 'b1'), (0, 8, 2) or (0, 9, 0, 'rc1')
# releaseDate format should be 'MM/DD/YY'.

# Update this to change the current version and release date:
# version = ('X', 'Y', 0)
version = (1, 1, 0)
# releaseDate = '@@/@@/@@'
releaseDate = '08/14/11'

# Verbose output (output unchanged files also):
verbose = False

from glob import glob
import os, sys, re

path = os.path.dirname(os.path.abspath(sys.argv[0]))
sys.path.append(path)
os.chdir(path)
print "Setversion", path


def versionString(version):
    """Create version string.

    For a sequence containing version information such as (2, 0, 0, 'pre'),
    this returns a printable string such as '2.0pre'.
    The micro version number is only excluded from the string if it is zero.

    """
    ver = map(str, version)
    numbers, rest = ver[:ver[2] == '0' and 2 or 3], ver[3:]
    return '.'.join(numbers) + '-'.join(rest)

versionString = versionString(version)

if versionString == 'X.Y':
    print "Please set the version."
    sys.exit(1)
if releaseDate == '@@/@@/@@':
    print "Please set the release date."
    sys.exit(1)


class Replacer:
    """Class to handle substitutions in a file."""

    def __init__(self, *args):
        self._subs = list(args)

    def add(self, search, replace):
        self._subs.append((re.compile(search,re.M), replace))

    def replaceInStr(self, data):
        for search, replace in self._subs:
            data = re.sub(search, replace, data)
        return data

    def replaceInFile(self, filename):
        data = open(filename).read()
        newdata = self.replaceInStr(data)
        if data == newdata:
            if verbose:
                print 'Unchanged ' + filename
        else:
            print 'Updating ' + filename
            open(filename, 'w').write(newdata)

    def replaceGlob(self, pattern):
        for file in glob(pattern):
            if os.path.exists(file):
                self.replaceInFile(file)


pyReplace = Replacer()
pyReplace.add(r"(__version__\s*=\s*)'.*'", r"\g<1>%s" % repr(versionString))

propReplace = Replacer()
propReplace.add(r"(version\s*=\s*).*", r"\g<1>%s" % repr(version))
propReplace.add(r"(releaseDate\s*=\s*).*", r"\g<1>%s" % repr(releaseDate))

htmlReplace = Replacer()
htmlReplace.add(r"<!--\s*version\s*-->[^<]*<!--\s*/version\s*-->",
        r"<!-- version --> %s <!-- /version -->" % versionString)
htmlReplace.add(r"<!--\s*relDate\s*-->[^<]*<!--\s*/relDate\s*-->",
        r"<!-- relDate --> %s <!-- /relDate -->" % releaseDate)

rstReplace = Replacer()
rstReplace.add(r"^:(.+)?: (X|\d+)\.(Y|\d+)\.\d+$", r":\1: %s" % versionString)
rstReplace.add(r"^:(.+)?: (@|\d){2}/(@|\d){2}/(@|\d){2}$", r":\1: %s" % releaseDate)

# Replace in Python files:
pyReplace.replaceGlob('*.py')
pyReplace.replaceGlob('DBUtils/*.py')
pyReplace.replaceGlob('DBUtils/*/*.py')

# Replace in Properties files:
propReplace.replaceGlob('DBUtils/Properties.py')

# Replace in existing HTML:
htmlReplace.replaceGlob('DBUtils/Docs/*.html')

# Replace in reStructuredText files:
rstReplace.replaceGlob('DBUtils/Docs/*.txt')
