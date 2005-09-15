# This modules handles win32 functions to run an external command and handle the priority
# of a process

import win32process
import win32api
import win32con
import os

def execute(commandline):
    startupInfo = win32process.STARTUPINFO()
    startupInfo.dwFlags = win32process.DETACHED_PROCESS | win32process.STARTF_USESHOWWINDOW
    startupInfo.wShowWindow = win32con.SW_HIDE
    hProcess, hThread, dwProcessId, dwThreadId = \
              win32process.CreateProcess(None, commandline, None,
                                         None, 0, 0, None, None,
                                         startupInfo)
    while (win32process.GetExitCodeProcess(hProcess) == win32con.STILL_ACTIVE):
        win32api.Sleep(2)

# to avoid a msdos command window to appear on screen
# def start(filename):
#       os.system('start "" "%s"' % filename)

def start(filename):
    print "current_dir = %s" % os.getcwd()
    execute('external\\windows\\start.bat "%s"' % filename)


def setIdlePriority():
    win32process.SetPriorityClass(win32api.GetCurrentProcess(), win32con.IDLE_PRIORITY_CLASS)
