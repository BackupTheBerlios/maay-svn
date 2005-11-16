"""
        Monitor the System (CPU load, memory)
"""

import win32pdh
import win32pdhutil
import locale

class SystemMonitor:
    def __init__(self):
        processor = win32pdhutil.find_pdh_counter_localized_name("Processor")
        processorTime = win32pdhutil.find_pdh_counter_localized_name("% Processor Time")

        path = win32pdh.MakeCounterPath((None,processor,"_Total", None, -1, processorTime))
        self.base = win32pdh.OpenQuery()
        self.__counter = win32pdh.AddCounter(self.base, path)
        win32pdh.CollectQueryData(self.base)
        # the function addCounter change the locale to the current locale (french ?)
        # and implies problems of float to string conversion (.5 => "0,5")
        locale.setlocale(locale.LC_ALL, None)
        self.__processorLoad = 0
        
        
        MEMORY = "Memory"
        COMMBYTES = "Available Bytes"
        memory = win32pdhutil.find_pdh_counter_localized_name(MEMORY)
        commbytes = win32pdhutil.find_pdh_counter_localized_name(COMMBYTES)

        path_comm = win32pdh.MakeCounterPath((None, memory, None, None, -1, commbytes))         
        self.base2 = win32pdh.OpenQuery()
        self.__counter2 = win32pdh.AddCounter(self.base2, path_comm)
        win32pdh.CollectQueryData(self.base2)
        # the function addCounter change the locale to the current locale (french ?)
        # and implies problems of float to string conversion (.5 => "0,5")
        locale.setlocale(locale.LC_ALL, None)

        self.__processorLoad = 0
        self.__availableMemory = 0
        
        locale.setlocale(locale.LC_ALL, "C")

    def update(self):
        win32pdh.CollectQueryData(self.base)
#               self.__processorLoad = win32pdh.GetFormattedCounterValue(self.__counter, win32pdh.PDH_FMT_LONG)[1]
        try:
            processorLoad = float(win32pdh.GetFormattedCounterValue(self.__counter, win32pdh.PDH_FMT_LONG)[1])
#               if processorLoad > self.__processorLoad:
#                       self.__processorLoad = processorLoad
#               else:
            if processorLoad > self.__processorLoad:
                alpha = .9
            else:
                alpha = .2
            self.__processorLoad = (1.0 - alpha) * self.__processorLoad + alpha * processorLoad

            win32pdh.CollectQueryData(self.base2)
            self.__availableMemory = win32pdh.GetFormattedCounterValue(self.__counter2, win32pdh.PDH_FMT_LONG)[1]
        except:
            pass


    def getProcessorLoad(self):
#               self.update()
        return self.__processorLoad

    def getAvailableMemory(self):
#               self.update()
        return self.__availableMemory
