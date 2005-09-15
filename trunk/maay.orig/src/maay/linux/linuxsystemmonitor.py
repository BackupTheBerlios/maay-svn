class SystemMonitor:
    def __init__(self):
        self.__idletime = 0
        self.__uptime = 0
        self.__cpuLoad = 0

    def update(self):
        fd = file('/proc/uptime')
        line = fd.readline()
        fd.close()
        infos = line.split()
        uptime = float(infos[0])
        idletime = float(infos[1])

        self.__cpuLoad = 100.0 - ((idletime - self.__idletime) / (uptime - self.__uptime)) * 100.0

        self.__uptime = uptime
        self.__idletime = idletime



    def getProcessorLoad(self):
        return self.__cpuLoad

    def getAvailableMemory(self):
        return 0
