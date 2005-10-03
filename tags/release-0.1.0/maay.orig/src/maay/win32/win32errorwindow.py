import sys
import win32gui
import win32api
import win32con
import struct, array
import commctrl
import Queue
import os

IDC_STATIC_EXCEPTION = 1024
IDC_EDIT_EXCEPTION = 1025
IDC_STATIC_LOG = 1026
IDC_EDIT_LOG = 1027
IDC_BUTTON_OK = 1028

WINDOW_WIDTH = 400
WINDOW_HEIGHT = 400

g_registeredClass = 0

#g_iconPathName = os.path.abspath(os.path.join( os.path.split(sys.executable)[0], "maayred.ico" ))
g_iconPathName = "maayred.ico"


class ErrorWindow:
    def __init__(self, exception, log_filename):
        win32gui.InitCommonControls()
        self.hinst = win32gui.dllhandle
        self.__exception = exception.replace("\n", "\r\n")
        

        fd = file(log_filename, 'r')
        content = fd.read()
        fd.close()
        content = content.replace("\n", "\r\n")
        self.__log = content

        self.list_data = {}
        self.hwnd = None
        self.DoModal()

        # right-justify the textbox.

        win32gui.PumpMessages()


    def _RegisterWndClass(self):
        className = "PythonDocSearch"
        global g_registeredClass
        if not g_registeredClass:
            message_map = {}
            wc = win32gui.WNDCLASS()
            wc.SetDialogProc() # Make it a dialog class.
            wc.hInstance = self.hinst
            wc.lpszClassName = className
            wc.style = win32con.CS_VREDRAW | win32con.CS_HREDRAW
            wc.hCursor = win32gui.LoadCursor( 0, win32con.IDC_ARROW )
            wc.hbrBackground = win32con.COLOR_WINDOW + 1
            wc.lpfnWndProc = message_map # could also specify a wndproc.
            # C code: wc.cbWndExtra = DLGWINDOWEXTRA + sizeof(HBRUSH) + (sizeof(COLORREF));
            wc.cbWndExtra = win32con.DLGWINDOWEXTRA + struct.calcsize("Pi")
            icon_flags = win32con.LR_LOADFROMFILE | win32con.LR_DEFAULTSIZE
            wc.hIcon = win32gui.LoadImage(self.hinst, g_iconPathName, win32con.IMAGE_ICON, 0, 0, icon_flags)
            classAtom = win32gui.RegisterClass(wc)
            g_registeredClass = 1
        return className

    def _GetDialogTemplate(self, dlgClassName):
        style = win32con.WS_THICKFRAME | win32con.WS_POPUP | win32con.WS_VISIBLE | win32con.WS_CAPTION | win32con.WS_SYSMENU | win32con.DS_SETFONT | win32con.WS_MINIMIZEBOX | win32con.ES_LEFT
        cs = win32con.WS_CHILD | win32con.WS_VISIBLE
        title = "Maay Error"

        # Window frame and title
        dlg = [ [title, (0, 0, WINDOW_WIDTH, WINDOW_HEIGHT), style, None, (8, "MS Sans Serif"), None, dlgClassName], ]

        s = cs
        dlg.append(['STATIC', "An error has occurred !", IDC_STATIC_EXCEPTION, (5, 5, WINDOW_WIDTH - 10, 10), s])

        s = cs | win32con.WS_BORDER | win32con.ES_MULTILINE | win32con.WS_VSCROLL | win32con.ES_AUTOVSCROLL | win32con.ES_READONLY | win32con.WS_HSCROLL
        dlg.append(['EDIT', self.__exception, IDC_EDIT_EXCEPTION, (5, 15, WINDOW_WIDTH - 10, 45), s])

        s = cs
        dlg.append(['STATIC', "Log", IDC_STATIC_LOG, (5, 70, WINDOW_WIDTH - 10, 10), s])

        s = cs | win32con.WS_BORDER | win32con.ES_MULTILINE | win32con.WS_VSCROLL | win32con.ES_AUTOVSCROLL | win32con.ES_READONLY | win32con.WS_HSCROLL
        dlg.append(['EDIT', self.__log, IDC_EDIT_LOG, (5, 80, WINDOW_WIDTH - 10, 80), s])
        
        s = cs | win32con.BS_DEFPUSHBUTTON
        dlg.append(["BUTTON", "OK", IDC_BUTTON_OK, (5, 180, WINDOW_WIDTH - 10, 14), s])

#        win32gui.UpdateWindow(self.hwnd)

        return dlg

    def CreateWindow(self):
        self._DoCreate(win32gui.CreateDialogIndirect)

    def DoModal(self):
        return self._DoCreate(win32gui.DialogBoxIndirect)

    def _DoCreate(self, fn):
        message_map = {
            win32con.WM_SIZE: self.OnSize,
            win32con.WM_COMMAND: self.OnCommand,
            win32con.WM_INITDIALOG: self.OnInitDialog,
            win32con.WM_CLOSE: self.OnClose,
            win32con.WM_DESTROY: self.OnDestroy
        }
        dlgClassName = self._RegisterWndClass()
        template = self._GetDialogTemplate(dlgClassName)
        return fn(self.hinst, template, 0, message_map)

    def OnInitDialog(self, hwnd, msg, wparam, lparam):
        self.hwnd = hwnd
        # centre the dialog
        desktop = win32gui.GetDesktopWindow()
        l,t,r,b = win32gui.GetWindowRect(self.hwnd)
        dt_l, dt_t, dt_r, dt_b = win32gui.GetWindowRect(desktop)
        centre_x, centre_y = win32gui.ClientToScreen( desktop, ( (dt_r-dt_l)/2, (dt_b-dt_t)/2) )
        win32gui.MoveWindow(hwnd, centre_x-(r/2), centre_y-(b/2), r-l, b-t, 0)
#        self._SetupList()
        l,t,r,b = win32gui.GetClientRect(self.hwnd)
        self._DoSize(r-l,b-t, 1)

    def OnClose(self, hwnd, msg, wparam, lparam):
        win32gui.EndDialog(hwnd, 0)

    def OnDestroy(self, hwnd, msg, wparam, lparam):
        print "OnDestroy"
        win32gui.PostQuitMessage(0) # Terminate the app.

    def _DoSize(self, cx, cy, repaint = 1):
        # right-justify the textbox.
        ctrl = win32gui.GetDlgItem(self.hwnd, IDC_STATIC_EXCEPTION)
        l, t, r, b = win32gui.GetWindowRect(ctrl)
        l, t = win32gui.ScreenToClient(self.hwnd, (l,t) )
        r, b = win32gui.ScreenToClient(self.hwnd, (r,b) )
        win32gui.MoveWindow(ctrl, 5, t, cx-l-5, b-t, repaint)

        # right-justify the textbox.
        ctrl = win32gui.GetDlgItem(self.hwnd, IDC_EDIT_EXCEPTION)
        l, t, r, b = win32gui.GetWindowRect(ctrl)
        l, t = win32gui.ScreenToClient(self.hwnd, (l,t) )
        r, b = win32gui.ScreenToClient(self.hwnd, (r,b) )
        win32gui.MoveWindow(ctrl, 5, t, cx-l-5, b-t, repaint)

        # right-justify the textbox.
        ctrl = win32gui.GetDlgItem(self.hwnd, IDC_STATIC_LOG)
        l, t, r, b = win32gui.GetWindowRect(ctrl)
        l, t = win32gui.ScreenToClient(self.hwnd, (l,t) )
        r, b = win32gui.ScreenToClient(self.hwnd, (r,b) )
        win32gui.MoveWindow(ctrl, 5, t, cx-l-5, b-t, repaint)

        # right-justify the textbox.
        ctrl = win32gui.GetDlgItem(self.hwnd, IDC_EDIT_LOG)
        l, t, r, b = win32gui.GetWindowRect(ctrl)
        l, t = win32gui.ScreenToClient(self.hwnd, (l,t) )
        r, b = win32gui.ScreenToClient(self.hwnd, (r,b) )
        win32gui.MoveWindow(ctrl, 5, t, cx-l-5, cy-190, repaint)

        # The button.
        ctrl = win32gui.GetDlgItem(self.hwnd, IDC_BUTTON_OK)
        l, t, r, b = win32gui.GetWindowRect(ctrl)
        l, t = win32gui.ScreenToClient(self.hwnd, (l,t) )
        r, b = win32gui.ScreenToClient(self.hwnd, (r,b) )
        list_y = b + 10
        w = r - l
        win32gui.MoveWindow(ctrl, 5, cy-40, cx-l-5, 25, repaint)


    def OnSize(self, hwnd, msg, wparam, lparam):
        x = win32api.LOWORD(lparam)
        y = win32api.HIWORD(lparam)
        self._DoSize(x,y)
        return 1


    def OnCommand(self, hwnd, msg, wparam, lparam):
        id = win32api.LOWORD(wparam)
        if id == IDC_BUTTON_OK:
            win32gui.PostQuitMessage(0) # Terminate the app.


