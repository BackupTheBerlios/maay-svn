"""
  Maay windows service
"""

import win32serviceutil
import win32evtlogutil
import win32event
import win32service
import win32process
import os
import sys

import maay.constants
import maay.maaymain

class MaayService(win32serviceutil.ServiceFramework):
    _svc_name_ = maay.constants.MAAY_SERVICE_NAME
    _svc_display_name_ = maay.constants.MAAY_SERVICE_NAME
    _svc_deps_ = [maay.constants.DBMS_SERVICE_NAME]
                           
    def __init__(self,args):
        win32serviceutil.ServiceFramework.__init__(self,args)
        self.__maay = None
        
    def SvcDoRun(self):
        self.Start_MaayService()                
        import servicemanager         
        win32evtlogutil.AddSourceToRegistry(self._svc_name_, servicemanager.__file__)
        servicemanager.Initialize(self._svc_name_, servicemanager.__file__)
        
        servicemanager.LogMsg(
                servicemanager.EVENTLOG_INFORMATION_TYPE,
                servicemanager.PYS_SERVICE_STARTED,
                (self._svc_name_,''))               


    def SvcStop(self):
        import servicemanager
        
        servicemanager.LogMsg(
                servicemanager.EVENTLOG_INFORMATION_TYPE,
                servicemanager.PYS_SERVICE_STOPPED,
                (self._svc_name_,''))
        
        try:                        
            self.Stop_MaayService()
        except:
            pass
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)                

 
    def Start_MaayService(self):
        self.__maay = maay.maaymain.Maay()
        si=win32process.STARTUPINFO()
        dir = os.path.dirname(sys.argv[0])
        os.chdir(dir)
        self.__maay.start()
                

    def Stop_MaayService(self):                     
        self.__maay.stop()
 
def installService():
    # TODO: change the dirty tricks to install the service...
    #dir = os.path.dirname(sys.argv[0])
    #if dir == '':
    #       dir = os.getcwd()

    
    sys.argv = ["win32maayservice.exe", "--interactive", 'install']
    print sys.argv
    win32serviceutil.HandleCommandLine(MaayService)
    
#       win32serviceutil.InstallService(
#               MaayService,
#                MaayService._svc_name_,
#                MaayService._svc_display_name_)
#        win32serviceutil.StartService(MaayService._svc_name_)

if __name__=='__main__':
    win32serviceutil.HandleCommandLine(MaayService)
