import os
import webbrowser

def execute(commandline):
    os.system(commandline)

def start(filename):
    webbrowser.open("file:////%s" % filename)

def setIdlePriority():
    pass
    
