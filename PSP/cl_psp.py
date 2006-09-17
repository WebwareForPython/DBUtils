
from ServletWriter import ServletWriter
# from PSPReader import PSPReader
from Context import *
from PSPCompiler import *

import os, sys

#move this to a class like JPS?

def PSPCompile(*args):
	pspfilename = args[0]
	fil, ext= os.path.basename(pspfilename).split('.')
	classname = fil + '_' + ext
	pythonfilename = classname + '.py'
	context = PSPCLContext(pspfilename)
	context.setClassName(classname)
	context.setPythonFileName(pythonfilename)
	clc = Compiler(context)
	clc.compile()

if __name__ == '__main__':
	PSPCompile(sys.argv[1])
