
"""This is the TaskManager Python package.

It provides a system for running any number of predefined tasks in separate
threads in an organized and controlled manner.

A task in this package is a class derived from the Task class. The task
should have a run method that, when called, performs some task.

The Scheduler class is the organizing object. It manages the addition,
execution, deletion, and well being of a number of tasks. Once you have
created your task class, you call the Scheduler to get it added to the
tasks to be run.

"""


from threading import Thread, Event
from TaskHandler import TaskHandler
from time import time, sleep
from exceptions import IOError

try: # for Python < 2.3
	True, False
except NameError:
	True, False = 1, 0


class Scheduler(Thread):
	"""The top level class of the TaskManager system.

	The Scheduler is a thread that handles organizing and running tasks.
	The Scheduler class should be instantiated to start a TaskManager sessions.
	Its start method should be called to start the TaskManager.
	Its stop method should be called to end the TaskManager session.

	"""


	## Init ##

	def __init__(self, daemon=True):
		Thread.__init__(self)
		self._notifyEvent = Event()
		self._nextTime = None
		self._scheduled = {}
		self._running = {}
		self._onDemand = {}
		self._isRunning = False
		if daemon:
			self.setDaemon(True)


	## Event Methods ##

	def wait(self, seconds=None):
		"""Our own version of wait().

		When called, it waits for the specified number of seconds, or until
		it is notified that it needs to wake up, through the notify event.

		"""
		try:
			self._notifyEvent.wait(seconds)
		except IOError, e:
			pass
		self._notifyEvent.clear()


	## Attributes ##

	def runningTasks(self):
		return self._running

	def running(self, name, default=None):
		"""Return running task with given name.

		Returns a task with the given name from the "running" list,
		if it is present there.

		"""
		return self._running.get(name, default)

	def hasRunning(self, name):
		"""Check to see if a task with the given name is currently running."""
		return self._running.has_key(name)

	def setRunning(self, handle):
		"""Add a task to the running dictionary.

		Used internally only.

		"""
		self._running[handle.name()] = handle

	def delRunning(self, name):
		"""Delete a task from the running list.

		Used Internally.

		"""
		try:
			handle = self._running[name]
			del self._running[name]
			return handle
		except:
			return None

	def scheduledTasks(self):
		return self._scheduled

	def scheduled(self, name, default=None):
		"""Return a task from the scheduled list."""
		return self._scheduled.get(name, default)

	def hasScheduled(self, name):
		"""Checks whether task with given name is in the scheduled list."""
		return self._scheduled.has_key(name)

	def setScheduled(self, handle):
		"""Add the given task to the scheduled list."""
		self._scheduled[handle.name()] = handle

	def delScheduled(self, name):
		"""Delete a task with the given name from the scheduled list."""
		try:
			handle = self._scheduled[name]
			del self._scheduled[name]
			return handle
		except:
			return None

	def onDemandTasks(self):
		return self._onDemand

	def onDemand(self, name, default=None):
		"""Return a task from the onDemand list."""
		return self._onDemand.get(name, default)

	def hasOnDemand(self, name):
		"""Checks whether task with given name is in the onDemand list?"""
		return self._onDemand.has_key(name)

	def setOnDemand(self, handle):
		"""Add the given task to the onDemand list."""
		self._onDemand[handle.name()] = handle

	def delOnDemand(self, name):
		"""Delete a task with the given name from the onDemand list."""
		try:
			handle = self._onDemand[name]
			del self._onDemand[name]
			return handle
		except:
			return None

	def nextTime(self):
		return self._nextTime

	def setNextTime(self, time):
		self._nextTime = time

	def isRunning(self):
		return self._isRunning


	## Adding Tasks ##

	def addTimedAction(self, time, task, name):
		"""Add a task to be run once, at a specific time."""
		handle = self.unregisterTask(name)
		if not handle:
			handle = TaskHandler(self, time, 0, task, name)
		else:
			handle.reset(time, 0, task, True)
		self.scheduleTask(handle)

	def addActionOnDemand(self, task, name):
		"""Add a task to be run only on demand.

		Adds a task to the scheduler that will not be scheduled
		until specifically requested.

		"""
		handle = self.unregisterTask(name)
		if not handle:
			handle = TaskHandler(self, time(), 0, task, name)
		else:
			handle.reset(time(), 0, task, True)
		self.setOnDemand(handle)

	def addDailyAction(self, hour, minute, task, name):
		"""Add an action to be run every day at a specific time.

		If a task with the given name is already registered with the
		scheduler, that task will be removed from the scheduling queue
		and registered anew as a periodic task.

		Can we make this addCalendarAction? What if we want to run
		something once a week? We probably don't need that for Webware,
		but this is a more generally useful module. This could be a
		difficult function, though. Particularly without mxDateTime.

		"""
		import time
		current = time.localtime(time.time())
		currHour = current[3]
		currMin = current[4]

		if hour > currHour:
			hourDifference = hour - currHour
			if minute > currMin:
				minuteDifference = minute - currMin
			elif minute < currMin:
				minuteDifference = 60 - currMin + minute
				hourDifference -= 1
			else:
				minuteDifference = 0
		elif hour < currHour:
			hourDifference = 24 - currHour + hour
			if minute > currMin:
				minuteDifference = minute - currMin
			elif minute < currMin:
				minuteDifference = 60 - currMin + minute
				hourDifference -= 1
			else:
				minuteDifference = 0
		else:
			if minute > currMin:
				hourDifference = 0
				minuteDifference = minute - currMin
			elif minute < currMin:
				minuteDifference = 60 - currMin + minute
				hourDifference = 23
			else:
				hourDifference = 0
				minuteDifference = 0

		delay = (minuteDifference + (hourDifference * 60)) * 60
		self.addPeriodicAction(time.time()+delay, 24*60*60, task, name)

	def addPeriodicAction(self, start, period, task, name):
		"""Add a task to be run periodically.

		Adds an action to be run at a specific initial time,
		and every period thereafter.

		The scheduler will not reschedule a task until the last
		scheduled instance of the task has completed.

		If a task with the given name is already registered with
		the scheduler, that task will be removed from the scheduling
		queue and registered anew as a periodic task.

		"""

		handle = self.unregisterTask(name)
		if not handle:
			handle = TaskHandler(self, start, period, task, name)
		else:
			handle.reset(start, period, task, True)
		self.scheduleTask(handle)


	## Task methods ##

	def unregisterTask(self, name):
		"""Unregisters the named task.

		After that it can be rescheduled with different parameters,
		or simply removed.

		"""
		handle = None
		if self.hasScheduled(name):
			handle = self.delScheduled(name)
		if self.hasOnDemand(name):
			handle = self.delOnDemand(name)
		if handle:
			handle.unregister()
		return handle

	def runTaskNow(self, name):
		"""Allow a registered task to be immediately executed.

		Returns True if the task is either currently running or was started,
		or False if the task could not be found in the list of currently
		registered tasks.

		"""
		if self.hasRunning(name):
			return True
		handle = self.scheduled(name)
		if not handle:
			handle = self.onDemand(name)
		if not handle:
			return False
		self.runTask(handle)
		return True

	def demandTask(self, name):
		"""Demand execution of a task.

		Allow the server to request that a task listed as being registered
		on-demand be run as soon as possible.

		If the task is currently running, it will be flagged to run again
		as soon as the current run completes.

		Returns False if the task name could not be found on the on-demand
		or currently running lists.

		"""
		if not self.hasRunning(name) and not self.hasOnDemand(name):
			return False
		else:
			handle = self.running(name)
			if handle:
				handle.runOnCompletion()
				return True
			handle = self.onDemand(name)
			if not handle:
				return False
			self.runTask(handle)
			return True

	def stopTask(self, name):
		"""Put an immediate halt to a running background task.

		Returns True if the task was either not running, or was
		running and was told to stop.

		"""
		handle = self.running(name)
		if not handle:
			return False
		handle.stop()
		return True

	def stopAllTasks(self):
		"""Terminate all running tasks."""
		for i in self._running.keys():
			print "Stopping ", i
			self.stopTask(i)

	def disableTask(self, name):
		"""Specify that a task be suspended.

		Suspended tasks will not be scheduled until later enabled.
		If the task is currently running, it will not be interfered
		with, but the task will not be scheduled for execution in
		future until re-enabled.

		Returns True if the task was found and disabled.

		"""
		handle = self.running(name)
		if not handle:
			handle = self.scheduled(name)
		if not handle:
			return False
		handle.disable()
		return True

	def enableTask(self, name):
		"""Enable a task again.

		This method is provided to specify that a task be re-enabled
		after a suspension. A re-enabled task will be scheduled for
		execution according to its original schedule, with any runtimes
		that would have been issued during the time the task was suspended
		simply skipped.

		Returns True if the task was found and enabled.

		"""
		handle = self.running(name)
		if not handle:
			handle = self.scheduled(name)
		if not handle:
			return False
		handle.enable()
		return True

	def runTask(self, handle):
		"""Run a task.

		Used by the Scheduler thread's main loop to put a task in
		the scheduled hash onto the run hash.

		"""
		name = handle.name()
		if self.delScheduled(name) or self.delOnDemand(name):
			self.setRunning(handle)
			handle.runTask()

	def scheduleTask(self, handle):
		"""Schedule a task.

		This method takes a task that needs to be scheduled and adds it
		to the scheduler. All scheduling additions or changes are handled
		by this method. This is the only Scheduler method that can notify
		the run() method that it may need to wake up early to handle a
		newly registered task.

		"""
		self.setScheduled(handle)
		if not self.nextTime() or handle.startTime() < self.nextTime():
			self.setNextTime(handle.startTime())
			self.notify()


	## Misc Methods ##

	def notifyCompletion(self, handle):
		"""Notify completion of a task.

		Used by instances of TaskHandler to let the Scheduler thread know
		when their tasks have run to completion. This method is responsible
		for rescheduling the task if it is a periodic task.

		"""
		name = handle.name()
		if self.hasRunning(name):
			self.delRunning(name)
			if handle.startTime() and handle.startTime() > time():
				self.scheduleTask(handle)
			else:
				if handle.reschedule():
					self.scheduleTask(handle)
				elif not handle.startTime():
					self.setOnDemand(handle)
					if handle.runAgain():
						self.runTask(handle)

	def notify(self):
		self._notifyEvent.set()

	def start(self):
		"""Start the scheduler's activity."""
		self._isRunning = True
		Thread.start(self)

	def stop(self):
		"""Terminate the scheduler and its associated tasks."""
		self._isRunning = False
		self.notify()
		self.stopAllTasks()
		# jdh: wait until the scheduler thread exits; otherwise
		# it's possible for the interpreter to exit before this thread
		# has a chance to shut down completely, which causes a traceback
		# cz: but use a timeout of 3 seconds, this should suffice
		self.join(3)


	## Main Method ##

	def run(self):
		"""Run task in a background thread.

		This method is responsible for carrying out the scheduling work of
		this class on a background thread. The basic logic is to wait until
		the next action is due to run, move the task from our scheduled
		list to our running list, and run it. Other synchronized methods
		such as runTask(), scheduleTask(), and notifyCompletion(), may
		be called while this method is waiting for something to happen.
		These methods modify the data structures that run() uses to
		determine its scheduling needs.

		"""
		while self._isRunning:
			if self.nextTime():
				nextTime = self.nextTime()
				currentTime = time()
				if currentTime < nextTime:
					sleepTime = nextTime - currentTime
					self.wait(sleepTime)
				if not self._isRunning:
					return
				currentTime = time()
				if currentTime >= nextTime:
					toRun = []
					nextRun = None
					for handle in self._scheduled.values():
						startTime = handle.startTime()
						if startTime <= currentTime:
							toRun.append(handle)
						else:
							if not nextRun:
								nextRun = startTime
							elif startTime < nextRun:
								nextRun = startTime
					self.setNextTime(nextRun)
					for handle in toRun:
						self.runTask(handle)
			else:
				self.wait()
