# encoding: utf-8

"""Main module, use this to run the application"""

from __future__ import unicode_literals
import wx
from wx.lib import dialogs
#from wx.lib import buttons
from wx.lib.agw import hyperlink
import wx.lib.newevent
import config
from networkhelpers import RefreshUserData, SetPrinterStatus, UserOffline, UserOnline, UserOffline_Blocking
from globals import *
import os.path
import sys
import platformspec
import webbrowser
import errors

if os.path.isfile(platformspec.configfilename):
    execfile(platformspec.configfilename)

# wx constants, globals and helpers
ID_EXIT = 1
ID_USER = 2
ID_STATUS_WINDOW = 3
ID_APPKEY = 4
ID_AUTOSTART = 5
ID_PROFILELINK = 6
ID_TIMER = 7
ID_PRINTER = 100
UserDataUpdated_Args, EVT_USER_DATA_UPDATED = wx.lib.newevent.NewEvent()

TIMER_INTERVAL = 5 * 60 * 1000 # in millisecs
TIMER_ERROR_INTERVAL = 15 * 1000

app = wx.App(redirect=False)

# Redirect stderr to error.log
stderr_original = sys.stderr
sys.stderr = open(platformspec.errorfilename, "w")
excepthook_original = sys.excepthook
def loggingexcepthook(exctype, value, traceback):
    """Closes the custom error stream if an unhandled exception occurs"""
    excepthook_original(exctype, value, traceback)
    # Restore stderr when done
    sys.stderr.close()
    sys.stderr = stderr_original
sys.excepthook = loggingexcepthook

class StderrLogger(wx.PyLog):
    """Logs wx messages to the error stream defined by sys.stderr"""
    def DoLogString(self, message, timestamp):
        sys.stderr.write(message + '\n')

wx.Log.SetActiveTarget(StderrLogger())

def ChangeAppKey(frame, callback):
    """
    Asks the user for a new appkey.
    If the user pressed cancel, the appkey remains unchanged.
    """
    global userconfig_appKey
    result = dialogs.textEntryDialog(frame, "Add meg az AppKey-edet:",
                                        "Új AppKey", userconfig_appKey)
    if result.accepted:
        userconfig_appKey = result.text
        RefreshUserData(userconfig_appKey, config.connectionURL, config.version, callback)

def AskForUpdate(frame):
    """Asks if the user wants to download the updated version
    of the client program.
    If she says yes, a browser window opens.
    Regardless of her choice, the program closes."""

    result = dialogs.messageDialog(frame,
                                   "A kliensből új verziót adtak ki. Szeretnéd most letölteni? Nemleges válasz esetén a program bezárul.",
                                   "Frissítés",
                                   wx.YES_NO)

    if result.accepted:
        webbrowser.open_new_tab(config.profileLink)

class Icons:
    """Container for all of the icons the application uses"""
    wait = wx.Icon(os.path.join(platformspec.imgpath, "printer_empty.png"), wx.BITMAP_TYPE_PNG)
    visible = wx.Icon(os.path.join(platformspec.imgpath, "printer.png"), wx.BITMAP_TYPE_PNG)
    invisible = wx.Icon(os.path.join(platformspec.imgpath, "printer_delete.png"), wx.BITMAP_TYPE_PNG)
    error = wx.Icon(os.path.join(platformspec.imgpath, "printer_error.png"), wx.BITMAP_TYPE_PNG)

class Bitmaps:
    """Container for all of the bitmaps the application uses"""
    visible = wx.Bitmap(os.path.join(platformspec.imgpath, "printer.png"), wx.BITMAP_TYPE_PNG)
    invisible = wx.Bitmap(os.path.join(platformspec.imgpath, "printer_delete.png"), wx.BITMAP_TYPE_PNG)
    online = wx.Bitmap(os.path.join(platformspec.imgpath, "bullet_green.png"), wx.BITMAP_TYPE_PNG)
    offline = wx.Bitmap(os.path.join(platformspec.imgpath, "bullet_red.png"), wx.BITMAP_TYPE_PNG)
    ok = wx.Bitmap(os.path.join(platformspec.imgpath, "accept.png"), wx.BITMAP_TYPE_PNG)
    error = wx.Bitmap(os.path.join(platformspec.imgpath, "error.png"), wx.BITMAP_TYPE_PNG)

# Forms, event handlers
class TaskIcon(wx.TaskBarIcon):
    """The printer icon in the notification area"""
    def __init__(self, frame):
        wx.TaskBarIcon.__init__(self)
        self.frame = frame

        self.SetIcon(Icons.wait, "Csatlakozás a printer szerverhez...")

        # Event Bindings
        frame.Bind(EVT_USER_DATA_UPDATED, self.OnUserDataUpdate)
        self.Bind(wx.EVT_MENU, self.OnAutoStart, id=ID_AUTOSTART)

    def CreatePopupMenu(self):
        menu = wx.Menu()

        if self.frame.IsShown():
            itemName = "Státusz ablak elrejtése"
        else:
            itemName = "Státusz ablak megjelenítése"
        item = wx.MenuItem(menu, ID_STATUS_WINDOW, itemName)
        font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
        font.SetWeight(wx.FONTWEIGHT_BOLD)
        item.SetFont(font)
        menu.AppendItem(item)
        menu.AppendSeparator()

        menu.Append(ID_APPKEY, "Új AppKey")
        item = wx.MenuItem(menu, ID_AUTOSTART, "Automatikus indítás")
        menu.AppendItem(item)
        item.SetCheckable(True)
        if platformspec.GetAutoStart():
            item.Check(True)
        menu.AppendSeparator()

        # Only allow the status menuitems if there are no errors
        with userDataLock:
            global userData
            if not userData.initialized:
                pass
            elif userData.error != None:
                pass
            else:
                if userData.status == True:
                    menu.Append(ID_USER, "Váltás elfoglalt állapotba")
                else:
                    menu.Append(ID_USER, "Váltás elérhető állapotba")

                if userData.GetPrinterCount() != 1:
                    i = 0
                    for printer in userData.GetPrinters():
                        pItem = wx.MenuItem(menu, ID_PRINTER + i, printer.name)
                        if printer.IsOn():
                            pItem.SetBitmap(Bitmaps.online)
                        else:
                            pItem.SetBitmap(Bitmaps.offline)
                        menu.AppendItem(pItem)
                        i = i + 1
                menu.AppendSeparator()

        menu.Append(ID_EXIT, "Kilépés")
        return menu

    def OnUserDataUpdate(self, e):
        with userDataLock:
            global userData
            if userData.error == None:
                if userData.status == True:
                    self.SetIcon(Icons.visible, userData.name + " elérhető (printer)")
                else:
                    self.SetIcon(Icons.invisible, userData.name + " elfoglalt (printer)")
            else:
                self.SetIcon(Icons.error, "Hiba (printer)")
        e.Skip()

    def OnAutoStart(self, e):
        platformspec.SetAutoStart(not platformspec.GetAutoStart())

class PrintersPanel(wx.Panel):
    """
    Helps with the layout of the printers.
    The number of printers is not known in advance,
    PrinterPanel makes it easier to manage this.
    """
    def __init__(self, parent, frame):
        wx.Panel.__init__(self, parent)

        self.parent = parent
        self.frame = frame

        self.buttons = list()
        self.images = list()

    def OnUserDataUpdate(self, e):
        """
        Called when the user's data changes.
        Updates all child controls to reflect the new data.
        """
        for button in self.buttons:
            button.Destroy()
        self.buttons = list()
        for image in self.images:
            image.Destroy()
        self.images = list()

        global userData

        with userDataLock:
            if userData.error != None: return
            i = 0
            sizer = wx.FlexGridSizer(userData.GetPrinterCount(), 2, hgap=5)
            for printer in userData.GetPrinters():
                cBitmap = wx.StaticBitmap(self, ID_PRINTER + i)
                if printer.IsOn():
                    cBitmap.SetBitmap(Bitmaps.online)
                else:
                    cBitmap.SetBitmap(Bitmaps.offline)
                sizer.Add(cBitmap, flag=wx.ALIGN_CENTER)
                button = wx.Button(self, ID_PRINTER + i, printer.name)
                sizer.Add(button, flag=wx.EXPAND)
                self.images.append(cBitmap)
                self.buttons.append(button)
                i = i + 1

        sizer.AddGrowableCol(1)

        self.SetSizerAndFit(sizer)



class StatusWindow(wx.Frame):
    """
    The main window of the application.
    It should handle almost all events.
    """
    def __init__(self):
        wx.Frame.__init__(self, None, wx.ID_ANY, "Printer - Nyomtatók állapota",
                          size=(350, 250))
        self.taskicon = TaskIcon(self)

        self.SetIcon(Icons.wait)

        # Widgets
        panel = wx.Panel(self)

        sizer = wx.FlexGridSizer(6, 2, 10, 10)
        self.sizer = sizer

        ALIGN_RIGHT_V = wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL
        ALIGN_LEFT_V = wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL

        # Name
        sizer.Add(wx.StaticText(panel, wx.ID_ANY, "Név:"), flag=ALIGN_RIGHT_V)
        self.nameStaticText = wx.StaticText(panel, wx.ID_ANY, "")
        namefont = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
        namefont.SetPointSize(12)
        self.nameStaticText.SetFont(namefont)
        sizer.Add(self.nameStaticText, flag=wx.ALIGN_CENTER)

        # Online/offline
        sizer.Add(wx.StaticText(panel, wx.ID_ANY, "Állapot:"), flag=ALIGN_RIGHT_V)

        statusSizer = wx.FlexGridSizer(1, 2, hgap=5)
        self.userstatusBitmap = wx.StaticBitmap(panel, ID_USER)
        statusSizer.Add(self.userstatusBitmap, flag=wx.ALIGN_CENTER)
        self.userstatusButton = wx.Button(panel, ID_USER, "")
        statusSizer.Add(self.userstatusButton, flag=wx.EXPAND)
        statusSizer.AddGrowableCol(1)
        sizer.Add(statusSizer, flag=wx.EXPAND)

        # Printers
        sizer.Add(wx.StaticText(panel, wx.ID_ANY, "Nyomtatók:"), flag=ALIGN_RIGHT_V)
        self.printerPanel = PrintersPanel(panel, self)
        sizer.Add(self.printerPanel, flag=wx.EXPAND)

        # AppKey
        sizer.Add(wx.StaticText(panel, wx.ID_ANY, "AppKey:"), flag=ALIGN_RIGHT_V)
        appKeySizer = wx.FlexGridSizer(1, 2, hgap=5)
        self.appKeyText = wx.StaticText(panel, ID_APPKEY, userconfig_appKey)
        appKeySizer.Add(self.appKeyText, flag=ALIGN_LEFT_V)
        self.appKeyButton = wx.Button(panel, ID_APPKEY, "Módosítás")
        appKeySizer.Add(self.appKeyButton, flag=wx.EXPAND)
        appKeySizer.AddGrowableCol(0)
        sizer.Add(appKeySizer, flag=wx.EXPAND)

        # PrinterProfilelink
        sizer.Add(wx.StaticText(panel, wx.ID_ANY, "Printer profil:"), flag=ALIGN_RIGHT_V)

        self.printerProfileLink = hyperlink.HyperLinkCtrl(panel, wx.ID_ANY, config.profileLink)
        sizer.Add(self.printerProfileLink, flag=ALIGN_LEFT_V)

        # Status message
        self.statusBitmap = wx.StaticBitmap(panel, wx.ID_ANY, Bitmaps.ok)
        sizer.Add(self.statusBitmap, flag=wx.ALIGN_CENTER)
        self.statusText = wx.StaticText(panel, wx.ID_ANY, "")
        sizer.Add(self.statusText, flag=wx.ALIGN_CENTER)


        sizer.AddGrowableCol(1)

        outerSizer = wx.BoxSizer()
        outerSizer.Add(sizer, flag=wx.ALL | wx.EXPAND, border=10, proportion=1)

        panel.SetSizerAndFit(outerSizer)

        self.Layout()

        # Create timer, but don't start it just yet
        self.timer = wx.Timer(self, ID_TIMER)
        self.nextErrorTicks = TIMER_ERROR_INTERVAL

        # Event bindings
        self.Bind(wx.EVT_CLOSE, self.OnClose)
        self.Bind(EVT_USER_DATA_UPDATED, self.OnUserDataUpdate)

        self.taskicon.Bind(wx.EVT_MENU, lambda e: self.Close(True), id=ID_EXIT)
        self.taskicon.Bind(wx.EVT_MENU, self.OnPrinter)
        self.Bind(wx.EVT_BUTTON, self.OnPrinter)
        self.taskicon.Bind(wx.EVT_TASKBAR_LEFT_DCLICK, self.ToggleVisible)
        self.taskicon.Bind(wx.EVT_MENU, self.ToggleVisible, id=ID_STATUS_WINDOW)
        self.taskicon.Bind(wx.EVT_MENU, self.OnUser, id=ID_USER)
        self.Bind(wx.EVT_BUTTON, self.OnUser, id=ID_USER)
        self.taskicon.Bind(wx.EVT_MENU, self.OnAppKey, id=ID_APPKEY)
        self.Bind(wx.EVT_BUTTON, self.OnAppKey, id=ID_APPKEY)
        self.Bind(wx.EVT_TIMER, self.OnTimer, id=ID_TIMER)

        # Save original appKey (see method UserDataFirstUpdated)
        self.originalAppKey = userconfig_appKey

        # Get userdata from printer server
        RefreshUserData(userconfig_appKey, config.connectionURL, config.version, self.UserDataFirstUpdated)

    def OnAppKey(self, e):
        """Called when the user clicks on the "Change appkey" button/menu"""
        ChangeAppKey(self, self.UserDataUpdated)

    def OnTimer(self, e):
        """
        Called when the timer ticks.
        It updates the server with status info, and tries to reconnect
        if an error occurs.
        """

        with userDataLock:
            if userData.status == True:
                UserOnline(userconfig_appKey, config.connectionURL, config.version, self.UserDataUpdated)
            else:
                UserOffline(userconfig_appKey, config.connectionURL, config.version, self.UserDataUpdated)

    def OnUserDataUpdate(self, e):
        """
        Called when the user's data changes.
        Updates all child controls to reflect the new data.
        """
        self.appKeyText.SetLabel(userconfig_appKey)
        with userDataLock:
            global userData
            if userData.requiredUpdate:
                self.Close(True)
                return
            if userData.error == None:
                self.nameStaticText.SetLabel(userData.name)
                self.userstatusButton.Enable()
                if userData.status == True:
                    self.SetIcon(Icons.visible)
                    self.userstatusBitmap.SetBitmap(Bitmaps.visible)
                    self.userstatusButton.SetLabel("Elérhető")
                    self.timer.Start(TIMER_INTERVAL, oneShot=True)
                else:
                    self.SetIcon(Icons.invisible)
                    self.userstatusBitmap.SetBitmap(Bitmaps.invisible)
                    self.userstatusButton.SetLabel("Elfoglalt")
                    # Only start the timer when the l
                    # No need to repeat "I'm not here"
                self.statusBitmap.SetBitmap(Bitmaps.ok)
                self.statusText.SetLabel("")

                self.nextErrorTicks = TIMER_ERROR_INTERVAL

            else:
                self.nameStaticText.SetLabel("")
                self.userstatusButton.Disable()
                self.SetIcon(Icons.error)
                self.statusBitmap.SetBitmap(Bitmaps.error)

                if isinstance(userData.error, errors.UserError):
                    errorMsg = userdata(userData.error)
                else:
                    errorMsg = "Hiba az alkalmazásban! Ha a hiba sokáig fennáll,\n" + \
                               "írj a kir-dev@sch.bme.hu címre!\n" + \
                               "A hiba szövege: " + unicode (userData.error) + "\n" + \
                               "Újrapróbálkozásig hátravan: " + unicode(self.nextErrorTicks) + " ms"
                    self.timer.Start(self.nextErrorTicks, oneShot=True)
                    self.nextErrorTicks = self.nextErrorTicks * 2

                self.statusText.SetLabel(errorMsg)

        self.printerPanel.OnUserDataUpdate(e)
        self.sizer.Layout()
        e.Skip()

    def UserDataUpdated(self):
        """Fires the UserDataUpdated event on the main window"""
        with userDataLock:
            if userData.requiredUpdate:
                AskForUpdate(self)
        wx.PostEvent(self, UserDataUpdated_Args())

    def UserDataFirstUpdated(self):
        """
        Called when the client fetches userdata for the first time.
        It loads the saved statuses from the config file
        """
        # appKey can be overwritten by a different thread - we need to original value
        #  - that's why it needs to be copied to a local variable
        # connectionURL does not change - so it does not need to be synchronized 
        with userDataLock:
            if userData.GetPrinterCount() == 1:
                userData.printers[0].status = userconfig_userStatus
            else:
                for printer in userData.GetPrinters():
                    if printer.id in userconfig_printerStatus:
                        printer.status = userconfig_printerStatus[printer.id]
            if userconfig_userStatus == 'on':
                UserOnline(self.originalAppKey, config.connectionURL, config.version, self.UserDataUpdated)
            else:
                UserOffline(self.originalAppKey, config.connectionURL, config.version, self.UserDataUpdated)

    def OnUser(self, e):
        """
        Called when the user clicks on the change status button/menu.
        Switches the user's status between online/offline."""
        with userDataLock:
            newStatus = not userData.status
        if newStatus == True:
            UserOnline(userconfig_appKey, config.connectionURL, config.version, self.UserDataUpdated)
        else:
            UserOffline(userconfig_appKey, config.connectionURL, config.version, self.UserDataUpdated)

        self.DisableButtons()

    def OnClose(self, e):
        """
        Called when the status window is about to be closed.
        If the user clicked on the close button, it just hides the window
        instead of closing.
        """
        if e.CanVeto():
            self.Hide()
        else:
            self.taskicon.Destroy()
            self.Destroy()

    def OnPrinter(self, e):
        """
        Called when the user clicks on one of the printers' button/menu.
        Toggles the status of the printer.
        """
        with userDataLock:
            printerNo = e.GetId() - ID_PRINTER
            if printerNo < 0 or printerNo >= userData.GetPrinterCount():
                # Allow event handlers for other menu items
                e.Skip()
                return

            printer = userData.GetPrinter(printerNo)

            #If there is only one printer, the printer's status cannot be changed, only the user's
            if userData.GetPrinterCount() == 1:
                self.OnUser(None)
                return

            SetPrinterStatus(userconfig_appKey, config.connectionURL, config.version, printer.id, not printer.IsOn(), self.UserDataUpdated)
            self.DisableButtons()


    def ToggleVisible(self, e):
        """Shows the window if it's hidden, hides it if it's shown."""
        if self.IsShown():
            self.Hide()
        else:
            self.Show()
            self.Raise()

    def DisableButtons(self):
        self.userstatusButton.Disable()
        for b in self.printerPanel.buttons:
            b.Disable()
        pass


# Main program

# Check for user config. If there is no AppKey, we have to ask the user
try:
    userconfig_appKey
except NameError:
    userconfig_appKey = ""
    userconfig_userStatus = "on"
    userconfig_printerStatus = {}
    result = dialogs.textEntryDialog(None, "Add meg az AppKey-edet:",
                                     "AppKey megadása", userconfig_appKey)
    if result.text == "":
        sys.exit()
    else:
        userconfig_appKey = result.text

frame = StatusWindow()
app.SetTopWindow(frame)
app.MainLoop()

# Save settings

with open(platformspec.configfilename, "w") as f:
    f.write("userconfig_appKey = " + repr(userconfig_appKey) + "\n")
    if userData.status == True:
        sStatus = "on"
    else:
        sStatus = "off"
    f.write("userconfig_userStatus = " + repr(sStatus) + "\n")
    d = {}
    for printer in userData.GetPrinters():
        d[printer.id] = printer.status
    f.write("userconfig_printerStatus = " + repr(d) + "\n")

# Make user offline

UserOffline_Blocking(userconfig_appKey, config.connectionURL, config.version, None)
