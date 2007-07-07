import os
import sys
import atexit


class ProcessRunning(Exception):
	pass


def removePidFile(pidfile):
	pidfile.remove()


class PidFile:

	def __init__(self, path):
		self._path = path
		self._createdPID = 0
		if os.path.exists(path):
			try:
				pid = int(open(path).read())
			except (IOError, ValueError, TypeError):
				# can't open file or read PID from file.  File is probably
				# invalid or stale, so try to delete it.
				pid = None
				print "%s is invalid or cannot be opened; " \
					"attempting to remove it." % path
				os.unlink(path) # should we catch errors here?
			else:
				if self.pidRunning(pid):
					raise ProcessRunning()
				else:
					print "%s is stale; removing." % path
					try:
						os.unlink(path)
					except OSError:
						# maybe the other process has just quit
						# and has removed the file.
						pass # try continuing...

		pidfile = open(path, 'w')
		pidfile.write(str(self.currentPID()))
		pidfile.close()

		self._createdPID = 1

		# Delete the pid file when python exits, so that the pid file is
		# removed if the process exits abnormally.
		# If the process crashes, though, the pid file will be left behind.
		atexit.register(removePidFile, self)

	def pidRunning(self, pid):
		if os.name == 'posix':
			try:
				os.kill(pid, 0)
			except OSError, e:
				if e.errno == 3: # No such process
					return 0
			return 1
		else:
			try:
				import win32api
				import win32con
				import pywintypes
				try:
					win32api.OpenProcess(
						win32con.PROCESS_QUERY_INFORMATION, 0, pid)
				except pywintypes.error, e:
					if e[0] == 87: # returned when process does not exist
						return 0
			except ImportError:
				pass # couldn't import win32 modules
			return 1

	def currentPID(self):
		if os.name == 'posix':
			return os.getpid()
		else:
			try:
				import win32api
			except ImportError:
				pass
			if sys.modules.has_key('win32api'):
				return win32api.GetCurrentProcessId()
		return None

	def __del__(self):
		self.remove()

	def remove(self):
		# Only remove the file if we created it. Otherwise attempting to start
		# a second process will remove the file created by the first.
		if self._createdPID:
			try:
				os.unlink(self._path)
			except OSError:
				pass
