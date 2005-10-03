"""
   Handles task-bar icon.
"""

import win32api
import win32gui
import win32con
import sys, os
import thread
import threading
import webbrowser

import maay.globalvars

SEARCH_MENU_ID = 1001
PREFERENCES_MENU_ID = 1002
HELP_MENU_ID = 1003
PAUSE_INDEXING_MENU_ID = 1004
RESUME_INDEXING_MENU_ID = 1005
EXIT_MENU_ID = 1006

INDEXER_PAUSED = 1
INDEXER_RUNNING = 2
INDEXER_IDLE = 3

class Win32MaayTaskbar:
    def __init__(self, maayMain):
        self.__maayMain = maayMain
        self.__startedLock = threading.Lock()
        self.__startedLock.acquire()

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
#               iconPathName = os.path.abspath(os.path.join( os.path.split(sys.executable)[0], "maaymain.exe" ))

        icon_flags = win32con.LR_LOADFROMFILE | win32con.LR_DEFAULTSIZE
        self.hicon = win32gui.LoadImage(hinst, "maay.ico", win32con.IMAGE_ICON, 0, 0, icon_flags)
        self.hicon_idle = win32gui.LoadImage(hinst, "maayred.ico", win32con.IMAGE_ICON, 0, 0, icon_flags)
        self.hicon_paused = win32gui.LoadImage(hinst, "maaybw.ico", win32con.IMAGE_ICON, 0, 0, icon_flags)

        flags = win32gui.NIF_ICON | win32gui.NIF_MESSAGE | win32gui.NIF_TIP
        nid = (self.hwnd, 0, flags, win32con.WM_USER+20, self.hicon, "Maay")
        win32gui.Shell_NotifyIcon(win32gui.NIM_ADD, nid)

        self.__startedLock.release()
        win32gui.PumpMessages()
#               win32gui.PumpWaitingMessages
        maay.globalvars.logger.info("STOP MAAY TASK BAR")
        

    def start(self):
        thread.start_new_thread(self.__start__, ())
        self.__startedLock.acquire()

    def OnRestart(self, hwnd, msg, wparam, lparam):
        self._DoCreateIcons()

    def OnDestroy(self, hwnd, msg, wparam, lparam):
        nid = (self.hwnd, 0)
        win32gui.Shell_NotifyIcon(win32con.NIM_DELETE, nid)
        win32gui.PostQuitMessage(0) # Terminate the app.

    def update(self):
        if maay.globalvars.indexer.isPaused():
            self.change(INDEXER_PAUSED, "Maay indexer is paused")
        elif maay.globalvars.indexer.isIdle():
            self.change(INDEXER_IDLE, "Maay indexer is idle\nLast file indexed: %s" % maay.globalvars.indexer.getCurrentFileName())
        else:
            self.change(INDEXER_RUNNING, "Maay indexer is running\nLast file indexed: %s" % maay.globalvars.indexer.getCurrentFileName())
            
    def change(self, state, tooltip):
        if state == INDEXER_IDLE:
            hicon = self.hicon_idle
        elif state == INDEXER_RUNNING:
            hicon = self.hicon
        elif state == INDEXER_PAUSED:
            hicon = self.hicon_paused

        flags = win32gui.NIF_ICON | win32gui.NIF_MESSAGE | win32gui.NIF_TIP
        nid = (self.hwnd, 0, flags, win32con.WM_USER+20, hicon, tooltip)
        win32gui.Shell_NotifyIcon(win32gui.NIM_MODIFY, nid)

    def OnTaskbarNotify(self, hwnd, msg, wparam, lparam):
        if lparam == win32con.WM_RBUTTONUP:
            menu = win32gui.CreatePopupMenu()
            win32gui.AppendMenu( menu, win32con.MF_STRING, SEARCH_MENU_ID, "Search")
            win32gui.AppendMenu( menu, win32con.MF_STRING, PREFERENCES_MENU_ID, "Preferences")
            win32gui.AppendMenu( menu, win32con.MF_STRING, HELP_MENU_ID, "Help" )
            win32gui.AppendMenu( menu, win32con.MF_SEPARATOR, 1002, "")
            if maay.globalvars.indexer.isPaused():
                win32gui.AppendMenu( menu, win32con.MF_STRING, PAUSE_INDEXING_MENU_ID, "Pause indexing for 15 minutes more")
                win32gui.AppendMenu( menu, win32con.MF_STRING, RESUME_INDEXING_MENU_ID, "Resume indexing")
            else:
                win32gui.AppendMenu( menu, win32con.MF_STRING, PAUSE_INDEXING_MENU_ID, "Pause indexing")
            win32gui.AppendMenu( menu, win32con.MF_STRING, EXIT_MENU_ID, "Exit" )
            win32gui.SetMenuDefaultItem(menu, SEARCH_MENU_ID, 0)
            pos = win32gui.GetCursorPos()
            # See http://msdn.microsoft.com/library/default.asp?url=/library/en-us/winui/menus_0hdi.asp
            win32gui.SetForegroundWindow(self.hwnd)
            win32gui.TrackPopupMenu(menu, win32con.TPM_LEFTALIGN, pos[0], pos[1], 0, self.hwnd, None)
            win32gui.PostMessage(self.hwnd, win32con.WM_NULL, 0, 0)
        elif lparam==win32con.WM_LBUTTONDBLCLK:
            webbrowser.open("http://127.0.0.1:%d/maay/resultspool" % maay.constants.MAAY_PORT, autoraise=1)
        return 1
        
    def OnDestroy(self, hwnd, msg, wparam, lparam):
        nid = (self.hwnd, 0)
        win32gui.Shell_NotifyIcon(win32gui.NIM_DELETE, nid)
        win32gui.PostQuitMessage(0) # Terminate the app.
        

    def showBalloon(self, title, msg):
        flags = win32gui.NIF_ICON | win32gui.NIF_MESSAGE | win32gui.NIF_INFO
        #define the icon properties (see http://msdn.microsoft.com/library/default.asp?url=/library/en-us/shellcc/platform/shell/reference/structures/notifyicondata.asp)
        nid = (self.hwnd, 0, flags, win32con.WM_USER+20, self.hicon, "", msg, 10, title, win32gui.NIIF_INFO)
        #change our already present icon ...
        win32gui.Shell_NotifyIcon(win32gui.NIM_MODIFY, nid)


    def OnCommand(self, hwnd, msg, wparam, lparam):
        id = win32api.LOWORD(wparam)
        if id == SEARCH_MENU_ID:
            webbrowser.open("http://127.0.0.1:%d/maay/resultspool" % maay.constants.MAAY_PORT, autoraise=1)
        elif id == PREFERENCES_MENU_ID:
            webbrowser.open("http://127.0.0.1:%d/maay/preferences" % maay.constants.MAAY_PORT, autoraise=1)
        elif id == HELP_MENU_ID:
            webbrowser.open("http://127.0.0.1:%d/maay/help" % maay.constants.MAAY_PORT, autoraise=1)
        elif id == PAUSE_INDEXING_MENU_ID:
            self.showBalloon("Maay", "Maay will not index your items for the next 15 minutes.")
            maay.globalvars.indexer.pause()
        elif id == RESUME_INDEXING_MENU_ID:
            self.showBalloon("Maay", "Maay has resumed indexing")
            maay.globalvars.indexer.resume()                        
        elif id == EXIT_MENU_ID:
            self.__maayMain.stop()

    def stop(self):
        nid = (self.hwnd, 0)
        win32gui.Shell_NotifyIcon(win32gui.NIM_DELETE, nid)
#               win32gui.PostMessage(self.hwnd, win32con.WM_QUIT, 0, 0)
#               self.OnDestroy()
#               win32gui.DestroyWindow(self.hwnd)
