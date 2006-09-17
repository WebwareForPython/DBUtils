"""
autotoc.py -- Create a table of contents from HTML headings.


USAGE

autotoc.py infile outfile

For use in a Python script, create an AutoToC instance::

    toc = AutoToC()

Then you can process strings with the process() method,
like that::

    input = open(infile).read()
    output = toc.process(input)
    open(outfile, 'w').write(output)

Insert the following directive in your HTML page at all places where you
want an automatically created table of contents to be inserted::

    <!-- contents -->

You can customize the title of the table of contents, the maximum depth
of headings to be regarded, a number of headings to be skipped and the
name of the class for the div element::

    <!-- contents(title='The table of contents:', classname='toc') -->
    <!-- contents(depth=3, skip=2) -->

By default, title='Contents', depth=6, skip=0 and classname='contents'.


DOWNLOAD

This script is part of Webware for Python.
You can download the latest version from the SVN repository
(http://svn.w4py.org/Webware/trunk/DocSupport/autotoc.py).


COPYRIGHT

Copyright (c) 2005 by Christoph Zwerschke.
Licensed under the Open Software License version 2.1.
"""

__version__ = '0.1'
__revision__ = "$Rev: ... $"
__date__ = "$Date$"


import sys, re


class ToC:
    """Auxiliary class representing a table of contents."""

    def __init__(self,
            title='Contents', depth=6, skip=0, classname='contents'):
        self._title = title
        if depth not in range(1, 7):
            depth = 6
        self._depth = depth
        self._skip = skip
        self._classname = classname
        self._pattern = None

    def make_html(self, headings, mindepth=1):
        """Make a table of contents from headings."""
        toc = ['<div class="%s">' % self._classname]
        if self._title:
            toc.append('\n<h%d>%s</h%d>' % (mindepth, self._title, mindepth))
        maxdepth = self._depth
        depth = mindepth - 1
        entries = {}
        for heading in headings[self._skip:]:
            if heading._depth < mindepth or heading._depth > maxdepth:
                continue
            while depth < heading._depth:
                toc.append('\n<ul>')
                depth += 1
                entries[depth] = 0
            while depth > heading._depth:
                if entries[depth]:
                    toc.append('</li>')
                toc.append('\n</ul>')
                depth -= 1
            if entries[depth]:
                toc.append('</li>')
            else:
                entries[depth] = 1
            toc.append('\n<li>')
            toc.append(heading.make_entry())
        while depth >= mindepth:
            if entries[depth]:
                toc.append('</li>')
            toc.append('\n</ul>')
            depth -= 1
        toc.append('\n</div>')
        return ''.join(toc)


class Heading:
    """Auxiliary class representing a heading."""

    def __init__(self, depth, title, name):
        self._depth = depth
        self._title = title
        self._name = name
        self._pattern = None
        self._replace = None

    def make_entry(self):
        """Make an entry in the table of contents."""
        if self._name:
            return '<a href="#%s">%s</a>' % (self._name, self._title)
        else:
            return self._title


class AutoToC:
    """Main class for automatic creation of table(s) of contents.

    Provides only one method process().

    """

    def __init__(self, depth=6):
        """Initialize the AutoToC processor.

        You may define a maximum depth here already.

        """
        if depth not in range(1, 7):
            depth = 6
        self._depth = depth
        self._whitespace_pattern = re.compile('\s+')
        self._toc_directive = re.compile(
            '(?P<pattern><!-- contents'
            '(?P<args>\(.*?\))? -->)')
        self._heading_pattern = re.compile(
            '(?P<pattern>(?:<a\s+name\s*=\s*["\'](?P<name>.*?)'
            '["\']\s*>\s*(?:</a>\s*)?)?<h(?P<depth>[1-6])(\s.*?)?>'
            '\s*(?P<title>.*?)\s*</h(?P=depth)>)', re.IGNORECASE)

    def process(self, input):
        """Create table(s) of contents and put them where indicated.

        Input and output are strings.

        """
        # Read in all contents directives:
        tocs_found = self._toc_directive.findall(input)
        if not tocs_found:
            return input # no table of contents directive in the input
        maxdepth = 0
        tocs = []
        group = self._toc_directive.groupindex
        for toc_found in tocs_found:
            p = toc_found[group['args'] - 1]
            if not p:
                p = '()'
            toc = eval('ToC' + p)
            toc._pattern = toc_found[group['pattern'] - 1]
            tocs.append(toc)
            if maxdepth <= toc._depth:
                maxdepth = toc._depth
        # Read in all headings:
        headings_found = self._heading_pattern.findall(input)
        if not headings_found:
            return input # no headings in the input
        mindepth = 6
        headings = []
        names = {}
        names_created = 0
        depths = {}
        group = self._heading_pattern.groupindex
        for heading_found in headings_found:
            names[heading_found[group['name'] - 1]] = 1
        for heading_found in headings_found:
            depth = int(heading_found[group['depth'] - 1])
            # truncate at max depth
            if depth > maxdepth:
                continue
            # get min depth with at least 2 headings
            if depth < mindepth:
                if depths.has_key(depth):
                    mindepth = depth
                else:
                    depths[depth] = 1
            title = heading_found[group['title'] - 1]
            name = heading_found[group['name'] - 1]
            if name:
                name_created = 0
            else: # no name given
                name = self._make_name(title) # create one
                if names.has_key(name): # make sure it is unique
                    n = names[name] + 1
                    while names.has_key('%s-%d' % (name, n)):
                        n += 1
                    name = '%s-%d' % (name, n)
                    names[name] = n
                else:
                    names[name] = 1
                names_created = name_created = 1
            heading = Heading(depth, title, name)
            heading._pattern = heading_found[group['pattern'] - 1]
            heading._name_created = name_created
            headings.append(heading)
        del names
        # Add missing link targets:
        if names_created:
            last_pos = 0
            output = []
            for heading in headings:
                pos = input.find(heading._pattern, last_pos)
                assert pos >= 0, 'Cannot find %r.' % heading._pattern
                output.append(input[last_pos:pos])
                last_pos = pos
                pos += len(heading._pattern)
                if heading._name_created:
                    output.append('<a name="%s"></a>' % heading._name)
                output.append(input[last_pos:pos])
                last_pos = pos
            output.append(input[last_pos:])
            input = ''.join(output)
            del output
        # Create table(s) of contents:
        last_pos = 0
        output = []
        for toc in tocs:
            pos = input.find(toc._pattern, last_pos)
            assert pos >= 0, 'Cannot find %r.' % toc._pattern
            output.append(input[last_pos:pos])
            last_pos = pos + len(toc._pattern)
            output.append(toc.make_html(headings, mindepth))
        output.append(input[last_pos:])
        return ''.join(output)

    # Auxiliary functions

    def _make_name(self, title):
        """Create a name from the title"""
        return self._whitespace_pattern.sub('-', title).lower()


def main(args):
    try:
        infile, outfile = args
    except:
        print __doc__
        sys.exit(2)
    toc = AutoToC()
    open(outfile, 'w').write(toc.process(open(infile).read()))

if __name__=='__main__':
	main(sys.argv[1:])
