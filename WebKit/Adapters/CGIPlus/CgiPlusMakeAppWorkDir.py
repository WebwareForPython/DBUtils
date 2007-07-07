#!/usr/bin/env python

"""MakeAppWorkDir.py

INTRODUCTION

This utility builds a directory tree that can be used as the current
working directory of an instance of the WebKit application server
in a WASD CGIPlus environment.

USAGE

MakeAppWorkDir.py [Options] WorkDir

Options:
  -c, --context-name=...  The name for the preinstalled context.
                          By default, it will be "MyContext".
  -d, --context-dir=...   The directory where the context will be located,
                          so you can place it outside of the WorkDir.
  -l, --library=...       Other dirs to be included in the search path.
                          You may specify this option multiple times.
  -i, --cvsignore         This will add .cvsignore files to the WorkDir.
  -u, --user=...          The name or uid of the user to own the WorkDir.
                          This option is supported under Unix only.
  -g, --group=...         The name or gid of the group to own the WorkDir.
                          This option is supported under Unix only.

WorkDir:
  The target working directory to be created.
"""

# FUTURE
# * Add options to immediately import the new directory tree into a
#   CVS or SVN repository. In the case of a CVS repository, the
#   .cvsignore files should be created automatically, and in case
#   of SVN, the corresponding svn propset commands should be issued.
# * MakeAppWorkDir.py should set the admin password like install.py does.
#   At the same time, install.py should be able to do a "app-less" install,
#   from which the admin can create appdirs using MakeAppWorkDir.py.
#   The idea here is that the results of install.py should only be "shared"
#   resources, and "per-app" resources (like the admin password) should be
#   deferred (or, at least, deferrable) to MakeAppWorkDir.py.
# CREDITS
# * Contributed to Webware for Python by Robin Dunn
# * Improved by Christoph Zwerschke

import sys, os, stat, re, glob, shutil


class MakeAppWorkDir:
	"""Make a new application runtime directory for Webware.

	This class breaks down the steps needed to create a new runtime
	directory for webware.  That includes all the needed
	subdirectories, default configuration files, and startup scripts.
	Each step can be overridden in a derived class if needed.
	"""

	def __init__(self, webwareDir, workDir, verbose=1, osType=None,
			contextName='MyContext', contextDir='', libraryDirs=None,
			cvsIgnore=0, uid=None, gid=None):
		"""Initializer for MakeAppWorkDir.

		Pass in at least the Webware directory and the target working
		directory. If you pass None for contextName then the default
		context will be the the WebKit/Examples directory as usual.

		"""
		self._webwareDir = webwareDir
		self._webKitDir = os.path.join(webwareDir, 'WebKit')
		self._workDir = os.path.abspath(workDir)
		self._verbose = verbose
		if osType is None:
			osType = os.name
		self._contextName = contextName
		self._contextDir = contextDir
		if libraryDirs is None:
			libraryDirs = []
		self._libraryDirs = libraryDirs
		self._osType = osType
		self._cvsIgnore = cvsIgnore
		self._uid = uid
		self._gid = gid

	def buildWorkDir(self):
		"""These are all the steps needed to make a new runtime directory.

		You can override the steps taken here with your own methods.

		"""
		self.msg("Making a new WebKit runtime directory...")
		self.msg()
		self.makeDirectories()
		self.copyConfigFiles()
		self.copyOtherFiles()
		self.makeLauncherScripts()
		if self._contextName is not None:
			self.makeDefaultContext()
		if self._cvsIgnore:
			self.addCvsIgnore()
		self.changeOwner()
		self.printCompleted()

	def makeDirectories(self):
		"""Create all the needed directories if they don't already exist."""
		self.msg("Creating the directory tree...")
		standardDirs = (
			'', 'Configs')
		for dir in standardDirs:
			dir = os.path.join(self._workDir, dir)
			if os.path.exists(dir):
				self.msg("\tWarning: %s already exists." % dir)
			else:
				os.mkdir(dir)
				self.msg("\t%s" % dir)
		for dir in self._libraryDirs:
			dir = os.path.join(self._workDir, dir)
			if not os.path.exists(dir):
				os.makedirs(dir)
				open(os.path.join(dir, '__init__.py'), 'w').write('#\n')
				self.msg("\t%s created." % dir)
		self.msg()

	def copyConfigFiles(self):
		"""Make a copy of the config files in the Configs directory."""
		self.msg("Copying config files...")
		configs = glob.glob(os.path.join(self._webKitDir,
			"Configs", "*.config"))
		for name in configs:
			newname = os.path.join(self._workDir, "Configs",
				os.path.basename(name))
			self.msg("\t%s" % newname)
			shutil.copyfile(name, newname)
			mode = os.stat(newname)[stat.ST_MODE]
			# remove public read/write/exec perms
			os.chmod(newname, mode & 0770)
		self.msg()

	def copyOtherFiles(self):
		"""Make a copy of any other necessary files in the new work dir."""
		self.msg("Copying other files...")
		otherFiles = ('error404.html',)
		for name in otherFiles:
			if name == 'AppServer':
				if self._osType == 'nt':
					name += '.bat'
				chmod = 1
			elif name == 'webkit':
				if self._osType != 'posix':
					continue
				chmod = 1
			else:
				chmod = 0
			newname = os.path.join(self._workDir, os.path.basename(name))
			if not os.path.exists(newname):
				oldname = os.path.join(self._webKitDir, name)
				if os.path.exists(oldname):
					self.msg("\t%s" % newname)
					shutil.copyfile(oldname, newname)
					if chmod:
						os.chmod(newname, 0755)
				else:
					self.msg("\tWarning: Cannot find %r." % oldname)
		self.msg()

	def makeLauncherScripts(self):
		"""Create the launcher scripts and copy the CGI adapter script."""
		self.msg("Creating the launcher scripts...")
		workDir = self._workDir
		webwareDir = self._webwareDir
		webKitDir = self._webKitDir
		libraryDirs = self._libraryDirs
		uid, gid = self._uid, self._gid
		if uid is None:
			user = None
		else:
			import pwd
			user = pwd.getpwuid(uid)[0]
		if gid is None:
			group = None
		else:
			import grp
			group = grp.getgrgid(gid)[0]
		executable = sys.executable
		scriptNames = launcherScripts.keys()
		scriptNames.sort()
		for name in scriptNames:
			if name.endswith('Service.py') and self._osType != 'nt':
				continue
			newname = os.path.join(workDir, name)
			if not os.path.exists(newname):
				oldname = os.path.join(webKitDir, name)
				if os.path.exists(oldname):
					self.msg("\t%s" % newname)
					script = launcherScripts[name] % locals()
					open(newname, "w").write(script)
					os.chmod(newname, 0755)
				else:
					self.msg("\tWarning: Cannot find %r." % oldname)
		self.msg()

	def makeDefaultContext(self):
		"""Make a very simple context for the newbie user to play with."""
		self.msg("Creating default context...")
		contextDir = os.path.join(
			self._workDir,
			self._contextDir or self._contextName)
		if contextDir.startswith(self._workDir):
			configDir = contextDir[len(self._workDir):]
			while configDir[:1] in (os.sep, os.altsep):
				configDir = configDir[1:]
		else:
			configDir = contextDir
		if not os.path.exists(contextDir):
			os.makedirs(contextDir)
		contextNames = exampleContext.keys()
		contextNames.sort()
		for name in contextNames:
			filename = os.path.join(contextDir, name)
			if not os.path.exists(filename):
				self.msg("\t%s" % filename)
				open(filename, "w").write(exampleContext[name])
		self.msg("Updating config for default context...")
		filename = os.path.join(self._workDir, "Configs",
			'Application.config')
		self.msg("\t%s" % filename)
		content = open(filename).readlines()
		output  = open(filename, 'w')
		foundContext = 0
		configDir = "WebKitPath + '/%s'" % (self._contextName,)
		for line in content:
			if line.startswith("Contexts['default'] = "):
				output.write("Contexts[%r] = %s\n"
					% (self._contextName, configDir))
				output.write("Contexts['default'] = %r\n"
					% self._contextName)
				foundContext += 1
			else:
				output.write(line)
		if not foundContext:
			self.msg("\tWarning: Default context could not be set.")
		self.msg()

	def addCvsIgnore(self):
		self.msg("Creating .cvsignore files...")
		files = {
			'.': '*.pyc\n*.pyo\n'
					'address.*\nhttpd.*\nappserverpid.*\nprofile.pstats',
			'Cache': '[a-zA-Z0-9]*',
			'ErrorMsgs': '[a-zA-Z0-9]*',
			'Logs': '[a-zA-Z0-9]*',
			'Sessions': '[a-zA-Z0-9]*',
			self._contextName: '*.pyc\n*.pyo'
		}
		for dir, contents in files.items():
			filename = os.path.join(self._workDir,
				dir, '.cvsignore')
			f = open(filename, 'w')
			f.write(contents)
			f.close()
		self.msg()

	def changeOwner(self):
		if self._uid is None and self._gid is None:
			return
		self.msg("Changing the ownership...")
		uid = self._uid
		if uid is None:
			uid =os.getuid()
		gid = self._gid
		if gid is None:
			gid = os.getgid()
		try:
			os.chown(self._workDir, uid, gid)
		except:
			self.msg("\tWarning: The ownership could not be changed.")
		else:
			for (dir, dirs, files) in os.walk(self._workDir):
				for file in dirs + files:
					path = os.path.join(dir, file)
					os.chown(path, uid, gid)
		self.msg()

	def printCompleted(self):
		run = os.path.abspath(os.path.join(self._workDir, 'AppServer'))
		print """
Congratulations, you've just created a runtime working directory for Webware.

Don't forget to set a correct security profile on this created directory tree.
The accounts which will execute the application need READ access to this
directory tree.


To finish you must create a CGIPlus script like the following
$ @WEBWARE092_ROOT:[VMS]CGIPlusLaunchWebKit -
        dev1:[users_directory] -
        dev2:[app_directory.MyAPP]

where
    dev1:[users_directory] is the directory which holds the directory
        created using the procedure WEBWARE092_ROOT:[VMS]add_webware_user.com
    dev2:[app_directory.MyAPP] is the directory created by this procedure


You will also need to add some rules to your HTTPD$MAP.CONF file
set /myapp/* map=once cache=noscript auth=once
set /myapp/* script=as=WEBWARE_USER
set /myapp/*  SCRIPT=SYNTAX=UNIX
set /myapp/* throttle=1/1,,,20,,00:05:00
script+ /myapp/* /cgi-bin/myapp.com*


if cgi-bin:[000000]myapp.com is the script previously mentioned.

Have fun!
"""

	def msg(self, text=None):
		if self._verbose:
			if text:
				print text
			else:
				print

launcherScripts = { # launcher scripts with adjusted parameters

} # end of launcher scripts

exampleContext = { # files copied to example context

# This is used to create a very simple sample context for the new
# work dir to give the newbie something easy to play with.

'__init__.py': r"""
def contextInitialize(appServer, path):
	# You could put initialization code here to be executed
	# when the context is loaded into WebKit.
	pass
""",

'Main.py': r"""
from WebKit.Page import Page

class Main(Page):

	def title(self):
		return 'My Sample Context'

	def writeContent(self):
		self.writeln('<h1>Welcome to Webware for Python!</h1>')
		self.writeln('''
		<p>This is a sample context generated for you and has purposly been kept
		very simple to give you something to play with to get yourself started.
		The code that implements this page is located in <b>%s</b>.</p>
		''' % self.request().serverSidePath())
		self.writeln('''
		<p>There are more examples and documentation in the Webware distribution,
		which you can get to from here:</p>
		<ul>
		''')
		servletPath = self.request().servletPath()
		contextName = self.request().contextName()
		ctxs = self.application().contexts().keys()
		ctxs.sort()
		for ctx in ctxs:
			if ctx in ('default', contextName) or '/' in ctx:
				continue
			self.writeln('<li><a href="%s/%s/">%s</a></li>'
				% (servletPath, ctx, ctx))
		self.writeln('</ul>')
"""

} # end of example context files

def usage():
	"""Print the docstring and exit with error."""
	print __doc__
	sys.exit(2)

def main(args=None):
	"""Evaluate the command line arguments and call MakeAppWorkDir."""
	if args is None:
		args = sys.argv[1:]
	contextName = contextDir = cvsIgnore = user = group = None
	libraryDirs = []
	# Get all options:
	from getopt import getopt, GetoptError
	try:
		opts, args = getopt(args, 'c:d:l:iu:g:', [
			'context-name=', 'context-dir=', 'library=',
			'cvsignore', 'user=', 'group='])
	except GetoptError, error:
		print str(error)
		usage()
	for opt, arg in opts:
		if opt in ('-c', '--context-name'):
			contextName = arg
		elif opt in ('-d', '--context-dir'):
			contextDir = arg
		elif opt in ('-l', '--library'):
			libraryDirs.append(arg)
		elif opt in ('-i', '--cvsignore'):
			cvsIgnore = 1
		elif opt in ('-u', '--user'):
			user = arg
		elif opt in ('-g', '--group'):
			group = arg
	# Get the name of the target directory:
	try:
		workDir = args.pop(0)
		workDir  = os.path.join(workDir, 'WebKit')
	except IndexError:
		usage()
	if args:# too many parameters
		usage()
	if os.path.exists(workDir):
		print "The target directory already exists!"
		sys.exit(1)
	if not contextName:
		if contextDir:
			contextName = os.path.basename(contextDir)
		else:
			contextName = 'MyContext'
	# Figure out the group id:
	gid = group
	if gid is not None:
		try:
			gid = int(gid)
		except ValueError:
			try:
				import grp
				entry = grp.getgrnam(gid)
			except KeyError:
				print 'Error: Group %r does not exist.' % gid
				sys.exit(2)
			except ImportError:
				print 'Error: Group names are supported under Unix only.'
				sys.exit(2)
			gid = entry[2]
	# Figure out the user id:
	uid = user
	if uid is not None:
		try:
			uid = int(uid)
		except ValueError:
			try:
				import pwd
				entry = pwd.getpwnam(uid)
			except KeyError:
				print 'Error: User %r does not exist.' % uid
				sys.exit(2)
			except ImportError:
				print 'Error: User names are supported under Unix only.'
				sys.exit(2)
			if not gid:
				gid = entry[3]
			uid = entry[2]
	# This assumes that this script is still located in Webware/bin:
	scriptName = sys.argv and sys.argv[0]
	if not scriptName or scriptName == '-c':
		scriptName = 'MakeAppWorkDir.py'
	binDir = os.path.dirname(os.path.abspath(scriptName))
	webwareDir = os.path.abspath(os.path.join(binDir, os.pardir))
	mawd = MakeAppWorkDir(webwareDir, workDir, 1, None,
		contextName, contextDir, libraryDirs, cvsIgnore, uid, gid)
	mawd.buildWorkDir() # go!

if __name__ == '__main__':
	main()
