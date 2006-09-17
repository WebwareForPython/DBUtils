"""
pytp.py -- A very simple Python Template Processor


USAGE

pytp.py infile outfile

For use in a Python script, create a PyTP instance::

    pytp = PyTP()

Then you can process strings with the process() method,
like that::

    input = open(infile).read()
    output = pytp.process(input)
    open(outfile, 'w').write(output)

You can also pass a scope to the process() method that will
be used by the Python code in the template.

The template processor evaluates instruction of this form::

    <%...%>

The starting and ending tag can be customized by setting
the tags parameter when creating the PyTP instance.
The default tags are those used by PSP. Other templating
languages use tags like::

    ('<?py', '?>') or ('<!--python', '-->') or ('[[' , ']]')

If the directive inside the tags starts with an equals sign,
it is considered as a Python expression to be evaluated. If
if the equals sign is missing, pytp will automatically find
out whether it is a Python expression or a Python statement.

* If it is a Python expression:
  - The expression will be evaluated and processed
    recursively as follows:
    * It if is a dictionary,
      use the sorted list of items on separate lines.
    * If it is any other iterable,
      use the list of items on separate lines.
    * Otherwise,
      use the conversion of the result to a string.
  - The processed result will be inserted in the output
    instead of the processing instruction.
* If it is a block of Python statements:
  - The statements will be executed.
  - Everything that is printed to standard output during
    execution will be inserted in the output instead of
    the processing instruction.


DOWNLOAD

This script is part of Webware for Python.
You can download the latest version from the SVN repository
(http://svn.w4py.org/Webware/trunk/DocSupport/pytp.py).

Note: Similar template processors have been written by:
* Christopher A. Craig (http://www.ccraig.org/software/pyhp/)
* David McNab (http://www.freenet.org.nz/python/pyweb/docs/pyhp.html)
* Alex Martelli (http://aspn.activestate.com/ASPN/Python/Cookbook/Recipe/52305)


COPYRIGHT

Copyright (c) 2005 by Christoph Zwerschke.
Licensed under the Open Software License version 2.1.
"""

__version__ = '0.1'
__revision__ = "$Rev: ... $"
__date__ = "$Date$"


import sys, re
try:
    from cStringIO import StringIO
except:
    raise
    from cStringIO import StringIO


class PyTP:
    """A very simple Python Template Processor.

    Provides only one method process().
    """

    def __init__(self, tags=None):
        """Initialize the Python template processor.

        You may define your own start and end tags here.
        """
        if tags is None:
            tags = ('<%', '%>')
        pattern = '%s(.*?)%s' % tuple(map(re.escape, tags))
        self._tags = re.compile(pattern, re.DOTALL)

    def process(self, input, scope=None):
        """Process a Python template.

        The input must be a string that will be returned
        with all tagged processing instructions expanded.

        You may also pass a variable scope for the
        processing instructions that must be a directory.

        """
        if scope is None:
            scope = {}
        stdout = sys.stdout
        output = []
        pos = 0
        while pos < len(input):
            m = self._tags.search(input, pos)
            if m is None:
                break
            pi = m.groups()[0].strip()
            isexpr = pi.startswith('=')
            if isexpr:
                pi = pi[1:].lstrip()
            try: # try to evaluate as Python expression
                out = eval(pi, scope)
                if out is None:
                    out = ''
            except SyntaxError:
                if isexpr:
                    line = input[:m.start()].count('\n') + 1
                    self._errmsg('expression syntax', line, pi)
                    raise
                out = None
            except:
                line = input[:m.start()].count('\n') + 1
                self._errmsg('expression', line, pi)
                raise
            if out:
                try:
                    out = self._output(out)
                except:
                    line = input[:m.start()].count('\n') + 1
                    self._errmsg('expression output', line, pi)
                    raise
            elif out is None:
                try: # try to evaluate as Python block
                    tempout = StringIO()
                    sys.stdout = tempout
                    try:
                        pi = self._adjust_block(pi)
                        exec pi in scope
                        out = tempout.getvalue()
                    finally:
                        sys.stdout = stdout
                        tempout.close()
                except:
                    line = input[:m.start()].count('\n') + 1
                    self._errmsg('statement', line, pi)
                    raise
            output.append(input[pos:m.start()])
            if out:
                output.append(out)
            pos = m.end()
        output.append(input[pos:])
        return ''.join(output)

    # Auxiliary functions

    def _output(self, something):
        """Output a Python object reasonably as string."""
        output = []
        if hasattr(something, 'items'):
            items = something.items
            try:
                items.sort()
            except:
                pass
            output.append(self._output(items))
        elif hasattr(something, '__iter__'):
            for s in something:
                output.append(self._output(s))
        else:
            if something is not None:
                output.append(str(something))
        while hasattr(something, 'next'):
            something = something.next
            if something is None:
                break
            output.append(self._output(something))
        return '\n'.join(output)

    def _errmsg(self, error, line, code):
        """Print an error message."""
        print 'PyTP %s error in line %d:' % (error, line)
        print code

    def _adjust_block(self, block, tab='\t'):
        """Adjust the indentation of a Python block."""
        lines = block.splitlines()
        lines = [lines[0].strip()] + [line.rstrip() for line in lines[1:]]
        ind = None # find least index
        for line in lines[1:]:
            if line != '':
                s = line.lstrip()
                if s[0] != '#':
                    i = len(line) - len(s)
                    if ind is None or i < ind:
                        ind = i
                        if i == 0:
                            break
        if ind is not None or ind != 0: # remove indentation
            lines[1:] = [line[:ind].lstrip() + line[ind:]
                for line in lines[1:]]
        block = '\n'.join(lines) + '\n'
        if lines[0] and not lines[0][0] == '#':
            # the first line contains code
            try: # try to compile it
                compile(lines[0], '<string>', 'exec')
                # if it works, line does not start new block
            except SyntaxError: # unexpected EOF while parsing?
                try: # try to compile the whole block
                    compile(block, '<string>', 'exec')
                    # if it works, line does not start new block
                except IndentationError: # expected an indented block?
                    # so try to add some indentation:
                    lines2 = lines[:1] + [tab + line for line in lines[1:]]
                    block2 = '\n'.join(lines2) + '\n'
                    # try again to compile the whole block:
                    compile(block2, '<string>', 'exec')
                    block = block2 # if it works, keep the indentation
                except:
                    pass # leave it as it is
            except:
                pass # leave it as it is
        return block


def main(args):
    try:
        infile, outfile = args
    except:
        print __doc__
        sys.exit(2)
    pytp = PyTP()
    open(outfile, 'w').write(toc.process(open(infile).read()))

if __name__=='__main__':
	main(sys.argv[1:])
