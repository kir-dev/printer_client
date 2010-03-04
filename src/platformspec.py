# encoding: utf-8
"""Platform specific functions and variables:
Autostart, file and folder paths"""

import os
import os.path
import sys

if os.name == 'nt':

    import _winreg

    root = _winreg.HKEY_CURRENT_USER

    def SetAutoStart(state):
        hKey = _winreg.OpenKey(root, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, _winreg.KEY_SET_VALUE)
        if state == True:
            _winreg.SetValueEx(hKey, "PrinterClient", 0, _winreg.REG_SZ, sys.executable)
        else:
            _winreg.DeleteValue(hKey, "PrinterClient")


    def GetAutoStart():
        hKey = _winreg.OpenKey(root, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, _winreg.KEY_READ)
        try:
            value, type = _winreg.QueryValueEx(hKey, "PrinterClient")
        except WindowsError:
            return False

        if type == _winreg.REG_SZ:
            return True
        else:
            return False

    imgpath = os.path.join(os.path.dirname(sys.executable), "res")
    if not os.path.isdir(os.environ['APPDATA'] + "/Kir-Dev"):
        os.mkdir(os.environ['APPDATA'] + "/Kir-Dev")
    configfilename = os.environ['APPDATA'] + "/Kir-Dev/PrinterClientConfig"
    errorfilename = os.environ['APPDATA'] + "/Kir-Dev/PrinterClientError.log"

    def WorkaroudSetFrame(frame):
        pass
        
    def WorkaroundSetCleanupFunc(func):
        pass

elif os.name == 'posix':

    def SetAutoStart(state):
        pass

    def GetAutoStart():
        pass
        
    __homepath = os.path.expanduser("~")

    imgpath = "res"
    configfilename = __homepath + "/.userconfig.py"
    errorfilename = __homepath + "/PrinterError.log"

    ID_WORKAROUND_TIMER = 1001
    
    def noop(e):
        pass

    timer = None
    def WorkaroundSetFrame(frame):
        global timer
        import wx
        timer = wx.Timer(frame, ID_WORKAROUND_TIMER)
        timer.Start(100)
        frame.Bind(wx.EVT_TIMER, noop, id=ID_WORKAROUND_TIMER)

    cleanupfunc = None
    def WorkaroundSetCleanupFunc(func):
        global cleanupfunc
        cleanupfunc = func
        
    import sys
    def DoCleanup():
        global cleanupfunc
        global timer
        if timer != None:
            timer.Stop()
        if cleanupfunc != None:
            cleanupfunc()
        sys.exit()
        

    import signal
    signal.signal(signal.SIGTERM, lambda val, stack: DoCleanup())
    signal.signal(signal.SIGHUP, lambda val, stack: DoCleanup())
    
