import os, sys
sys.path.insert(1, os.path.abspath(os.path.join(os.pardir, os.pardir)))
import TaskKit

from TaskKit.Scheduler import Scheduler
from TaskKit.Task import Task
from time import time, sleep


class SimpleTask(Task):

	def run(self):
		if self.proceed():
			print self.name(), time()
			# print "Increasing period"
			# self.handle().setPeriod(self.handle().period()+2)
		else:
			print "Should not proceed", self.name()
			print "proceed for %s=%s, isRunning=%s" % (self.name(), self.proceed(), self._handle._isRunning)


class LongTask(Task):
	def run(self):
		while 1:
			sleep(2)
			print "proceed for %s=%s, isRunning=%s" % (self.name(), self.proceed(), self._handle._isRunning)
			if self.proceed():
				print ">>",self.name(), time()
			else:
				print "Should not proceed:", self.name()
				return

def main():
	from time import localtime
	scheduler = Scheduler()
	scheduler.start()
	scheduler.addPeriodicAction(time(), 1, SimpleTask(), 'SimpleTask1')
	scheduler.addTimedAction(time()+3, SimpleTask(), 'SimpleTask2')
	scheduler.addActionOnDemand(LongTask(), 'LongTask')
	scheduler.addDailyAction(localtime(time())[3], localtime(time())[4]+1, SimpleTask(), "DailyTask")
	sleep(5)
	print "Demanding LongTask"
	scheduler.runTaskNow('LongTask')
	sleep(1)
	# print "Stopping LongTask"
	# scheduler.stopTask("LongTask")
	sleep(2)
	# print "Deleting 'SimpleTask1'"
	# scheduler.unregisterTask("SimpleTask1")
	sleep(4)
	print "Calling stop"
	scheduler.stop()
	sleep(2)
	print "Test Complete"


if __name__=='__main__':
	main()
