
from time import time, sleep
from threading import Event, Thread

try: # for Python < 2.3
	True, False
except NameError:
	True, False = 1, 0


class TaskHandler:
	"""The task handler.

	While the Task class only knows what task to perform with the run()-method,
	the TaskHandler has all the knowledge about the periodicity of the task.
	Instances of this class are managed by the Scheduler in the scheduled,
	running and onDemand dictionaries.

	"""


	## Init ##

	def __init__(self, scheduler, start, period, task, name):
		self._scheduler = scheduler
		self._task = task
		self._name = name
		self._thread = None
		self._isRunning = False
		self._suspend = False
		self._lastTime = None
		self._startTime = start
		self._registerTime = time()
		self._reregister = True
		self._rerun = False
		self._period = abs(period)


	## Scheduling ##

	def reset(self, start, period, task, reregister):
		self._startTime = start
		self._period = abs(period)
		self._task = task
		self._reregister = reregister

	def runTask(self):
		"""Run this task in a background thread."""
		if self._suspend:
			self._scheduler.notifyCompletion(self)
			return
		self._rerun = False
		self._thread = Thread(None, self._task._run, self.name(), (self,))
		self._isRunning = True
		self._thread.start()

	def reschedule(self):
		"""Determine whether this task should be rescheduled.

		Increments the startTime and returns true if this is
		a periodically executed task.

		"""
		if self._period == 0:
			return False
		else:
			if self._lastTime - self._startTime > self._period:
				# if the time taken to run the task exceeds the period
				self._startTime = self._lastTime + self._period
			else:
				self._startTime += self._period
			return True

	def notifyCompletion(self):
		self._isRunning = False
		self._lastTime = time()
		self._scheduler.notifyCompletion(self)


	## Attributes ##

	def isRunning(self):
		return self._isRunning

	def runAgain(self):
		"""
		This method lets the Scheduler check to see whether this task should be
		re-run when it terminates
		"""
		return self._rerun

	def isOnDemand(self):
		"""Return True if this task is not scheduled for periodic execution."""
		return self._period == 1

	def runOnCompletion(self):
		"""Request that this task be re-run after its current completion.

		Intended for on-demand tasks that are requested by the Scheduler while
		they are already running.

		"""
		self._rerun = True

	def unregister(self):
		"""Request that this task not be kept after its current completion.

		Used to remove a task from the scheduler.

		"""
		self._reregister = False
		self._rerun = False

	def disable(self):
		"""Disable future invocations of this task."""
		self._suspend = True

	def enable(self):
		"""Enable future invocations of this task."""
		self._suspend = False

	def period(self):
		"""Return the period of this task."""
		return self._period

	def setPeriod(self, period):
		"""Change the period for this task."""
		self._period = period

	def stop(self):
		self._isRunning = False

	def name(self):
		return self._name

	def startTime(self, newTime=None):
		if newTime:
			self._startTime = newTime
		return self._startTime
