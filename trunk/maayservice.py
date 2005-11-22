#     Maay : a network of peers for document search
#
#     Copyright (C) 2005 France Telecom R&D
#
#     This library is free software; you can redistribute it and/or
#     modify it under the terms of the GNU Lesser General Public
#     License as published by the Free Software Foundation; either
#     version 2.1 of the License, or (at your option) any later version.
#
#     This library is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#     Lesser General Public License for more details.
#
#     You should have received a copy of the GNU Lesser General Public
#     License along with this library; if not, write to the Free Software
#     Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

__revision__ = '$Id$'

import win32serviceutil
import win32service
import win32event
import win32evtlogutil

import win32api
import win32gui
import win32con
import sys, os
import thread
import webbrowser
import maayservice


from twisted.internet import reactor

# display small icons on bottom right corner to notify user that maay is running
# maybe need some refactoring

class Win32MaayTaskbar:
    SEARCH_MENU_ID = 1001
    INDEXATION_MENU_ID = 1002
    HOMEPAGE_MENU_ID = 1003
        
    def __init__(self, node):
        self.node = node

    def __start__(self):
        msg_TaskbarRestart = win32api.RegisterWindowMessage("TaskbarCreated");
        message_map = {
                msg_TaskbarRestart: self.OnRestart,
                win32con.WM_DESTROY: self.OnDestroy,
                win32con.WM_COMMAND: self.OnCommand,
                win32con.WM_USER+20 : self.OnTaskbarNotify,
        }
        # Register the Window class.
        wc = win32gui.WNDCLASS()
        hinst = wc.hInstance = win32gui.GetModuleHandle(None)
        wc.lpszClassName = "MaayTaskbar"
        wc.style = win32con.CS_VREDRAW | win32con.CS_HREDRAW;
        wc.hCursor = win32gui.LoadCursor( 0, win32con.IDC_ARROW )
        wc.hbrBackground = win32con.COLOR_WINDOW
        wc.lpfnWndProc = message_map # could also specify a wndproc.
        classAtom = win32gui.RegisterClass(wc)
        # Create the Window.
        style = win32con.WS_OVERLAPPED | win32con.WS_SYSMENU
        self.hwnd = win32gui.CreateWindow( classAtom, "Maay", style, \
                0, 0, win32con.CW_USEDEFAULT, win32con.CW_USEDEFAULT, \
                0, 0, hinst, None)
        win32gui.UpdateWindow(self.hwnd)

        # Try and find a custom icon
        hinst =  win32gui.GetModuleHandle(None)
#        iconPathName = os.path.abspath(os.path.join( os.path.split(sys.executable)[0], "maay_node.exe" ))

        icon_flags = win32con.LR_LOADFROMFILE | win32con.LR_DEFAULTSIZE
        self.hicon = win32gui.LoadImage(hinst, "data\\images\\maay.ico", win32con.IMAGE_ICON, 0, 0, icon_flags)

        flags = win32gui.NIF_ICON | win32gui.NIF_MESSAGE | win32gui.NIF_TIP
        nid = (self.hwnd, 0, flags, win32con.WM_USER+20, self.hicon, "Maay")
        win32gui.Shell_NotifyIcon(win32gui.NIM_ADD, nid)

        win32gui.PumpMessages()
        

    def start(self):
        thread.start_new_thread(self.__start__, ())

    def OnRestart(self, hwnd, msg, wparam, lparam):
        self._DoCreateIcons()

    def OnDestroy(self, hwnd, msg, wparam, lparam):
        nid = (self.hwnd, 0)
        Shell_NotifyIcon(NIM_DELETE, nid)
        PostQuitMessage(0) # Terminate the app.


    def OnTaskbarNotify(self, hwnd, msg, wparam, lparam):
        if lparam == win32con.WM_RBUTTONUP:
            menu = win32gui.CreatePopupMenu()
            win32gui.AppendMenu( menu, win32con.MF_STRING, Win32MaayTaskbar.SEARCH_MENU_ID, "Search")
            win32gui.AppendMenu( menu, win32con.MF_STRING, Win32MaayTaskbar.INDEXATION_MENU_ID, "Manage Folders")
            win32gui.AppendMenu( menu, win32con.MF_SEPARATOR, 1002, "")
            win32gui.AppendMenu( menu, win32con.MF_STRING, Win32MaayTaskbar.HOMEPAGE_MENU_ID, "Maay Homepage")
            win32gui.SetMenuDefaultItem(menu, Win32MaayTaskbar.SEARCH_MENU_ID, 0)
            pos = win32gui.GetCursorPos()
            # See http://msdn.microsoft.com/library/default.asp?url=/library/en-us/winui/menus_0hdi.asp
            win32gui.SetForegroundWindow(self.hwnd)
            win32gui.TrackPopupMenu(menu, win32con.TPM_LEFTALIGN, pos[0], pos[1], 0, self.hwnd, None)
            win32gui.PostMessage(self.hwnd, win32con.WM_NULL, 0, 0)
        elif lparam==win32con.WM_LBUTTONDBLCLK:
            webbrowser.open("http://127.0.0.1:%s/" % self.node.nodeConfig.webserver_port, autoraise=1)
        return 1

    def OnCommand(self, hwnd, msg, wparam, lparam):
        id = win32api.LOWORD(wparam)
        if id == Win32MaayTaskbar.SEARCH_MENU_ID:
            webbrowser.open("http://127.0.0.1:%s/" % self.node.nodeConfig.webserver_port, autoraise=1)
        elif id == Win32MaayTaskbar.INDEXATION_MENU_ID:
            webbrowser.open("http://127.0.0.1:%s/indexation" % self.node.nodeConfig.webserver_port, autoraise=1)
        elif id == Win32MaayTaskbar.HOMEPAGE_MENU_ID:
            webbrowser.open("http://maay.netofpeers.net", autoraise=1)


class MyService(win32serviceutil.ServiceFramework):
    _svc_name_ = "Maay"
    _svc_display_name_ = "Maay"
    _svc_deps_ = ["EventLog", "MySQL"]
    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        reactor.stop()

    def SvcDoRun(self):
        import servicemanager
        import maay.node
        win32evtlogutil.ReportEvent(self._svc_name_,
                                    servicemanager.PYS_SERVICE_STARTED,
                                    0, # category
                                    servicemanager.EVENTLOG_INFORMATION_TYPE,
                                    (self._svc_name_, ''))
        taskbar = Win32MaayTaskbar(maay.node)
        taskbar.start()
        maay.node.run()
        # and write a 'stopped' event to the event log.
        win32evtlogutil.ReportEvent(self._svc_name_,
                                    servicemanager.PYS_SERVICE_STOPPED,
                                    0, # category
                                    servicemanager.EVENTLOG_INFORMATION_TYPE,
                                    (self._svc_name_, ''))


if __name__ == '__main__':
    # Note that this code will not be run in the 'frozen' exe-file!!!
    win32serviceutil.HandleCommandLine(MyService)
