""" This module is used to update periodically some score.
It will be used to manage aging (old score are less good than new one).
"""

import thread
import threading
import time

import globalvars


#import signal
#class TimeoutError (Exception): pass
#def SIGALRM_handler(sig, stack): raise TimeoutError()

#signal.signal(signal.SIGALRM, SIGALRM_handler)

class Task:
    def __init__(self, name, function, stop_function, period):
        globalvars.logger.info("Initializing task %s" % name)
        self.__name = name
        self.__function = function
        self.__stop_function = stop_function
        self.__period = period
        self.__running = 0
        self.t = 0
        self.__runningLock = threading.Lock()

    def __run(self):
        while self.__running:
            self.__runningLock.acquire()
            try:
                self.__function()
            except:
                raise "exception during call of %s" % self.__function
            self.__runningLock.release()
            self.t = 0
            while self.t < self.__period and self.__running == 1:
                self.t += 2
                time.sleep(2)

    def start(self):
        self.__running = 1
        t = thread.start_new_thread(self.__run, ())

    def stop(self):
        self.__running = 0
        if self.__stop_function:
            self.__stop_function()

    def force(self):
        self.t = self.__period + 1

    def get_name(self):
        return self.__name

class TaskScheduler:
    def __init__(self):
        self.__tasks = []
        self.__taskHT = {}

    def add(self, task_name, function, stop_function, period):
        task = Task(task_name, function, stop_function, period)
        self.__tasks.append(task)
        self.__taskHT[task_name] = task

    def start(self):
        for task in self.__tasks:
            task.start()

    def stop(self):
        for task in self.__tasks:
            globalvars.logger.info("Waiting task '%s' to stop" % task.get_name())
            task.stop()
            globalvars.logger.info("Task '%s' stopped" % task.get_name())

        # todo with using signal...

    def force_task(self, task_name):
        self.__taskHT[task_name].force()
