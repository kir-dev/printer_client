# encoding: utf-8

import webcom
import errors
from threading import *
from globals import *

class NetworkStatusUpdateThread(Thread):
    """
    A thread that sends the printers' statuses to the printer server.
    """
    def __init__(self, appKey, host, version, printerId, status):
        Thread.__init__(self)
        self.appKey = appKey
        self.host = host
        self.printerId = printerId
        self.status = status
        self.version = version

    def run(self):
        global userData
        try:
            webcom.SetPrinterStatus(self.appKey, self.host, self.version, self.printerId, self.status)
        except errors.UpdateError:
            userData.requiredUpdate = True
        except Exception as ex:
            with userDataLock:
                userData.error = ex
        else:
            with userDataLock:
                userData.error = None
        finally:
            with userDataLock:
                if userData.status == False and userData.GetPrinterCount() != 1: return
                for p in userData.GetPrinters():
                    if p.id == self.printerId:
                        p.status = self.status


class NetworkGetUserDataThread(Thread):
    """
    A thread that fetches the user's data from the printer server.
    """
    def __init__(self, appKey, host, version):
        Thread.__init__(self)
        self.appKey = appKey
        self.host = host
        self.version = version

    def run(self):
        global userData
        try:
            newUserData = webcom.GetUserData(self.appKey, self.host, self.version)
            with userDataLock:
                userData.CopyFrom(newUserData)
        except errors.UpdateError:
            userData.requiredUpdate = True
        except Exception as ex:
            with userDataLock:
                userData.error = ex
        else:
            with userDataLock:
                userData.error = None

class ThreadWaiter(Thread):
    """
    A thread that waits for other threads to finish.
    When all the threads are joined into this thread, a callback is called
    to notify other parts of the system.
    """
    def __init__(self, funcWhenReady):
        Thread.__init__(self)
        self.func = funcWhenReady
        self.threads = []

    def add(self, thread):
        """Adds a thread to the waiting queue"""
        self.threads.append(thread)

    def run(self):
        for thread in self.threads:
            thread.join()
        if self.func != None:
            self.func()

def RefreshUserData(appKey, host, version, callback):
    """
    Fetches the status of the printers and the user in a separate thread.
    The callback is called when the update is finished.
    """
    thread = NetworkGetUserDataThread(appKey, host, version)
    thread.start()
    wthread = ThreadWaiter(callback)
    wthread.add(thread)
    wthread.start()

def StatusToString(status):
    if status == True:
        return "on"
    else:
        return "off"

def SetPrinterStatus(appKey, host, version, printerId, status, callback):
    """
    Sets the status of a printer in a separate thread.
    The callback is called when the update is finished.
    """
    with userDataLock:
        if userData.status == False:
            userData.GetPrinterFromId(printerId).status = StatusToString(status)
            callback()
            return
    thread = NetworkStatusUpdateThread(appKey, host, version, printerId, StatusToString(status))
    thread.start()
    wthread = ThreadWaiter(callback)
    wthread.add(thread)
    wthread.start()

def UserOffline_Internal(appKey, host, version, callback):
    """Sets the status of the user (all of her printers) to offline.
    Returns the "waiting" thread."""
    with userDataLock:
        global userData
        userData.status = False
        wthread = ThreadWaiter(callback)
        for printer in userData.GetPrinters():
            thread = NetworkStatusUpdateThread(appKey, host, version, printer.id, "off")
            thread.start()
            wthread.add(thread)
    wthread.start()
    return wthread

def UserOffline(appKey, host, version, callback):
    """Sets the status of the user (all of her printers) to offline."""
    UserOffline_Internal(appKey, host, version, callback)

def UserOffline_Blocking(appKey, host, version, callback):
    """Sets the status of the user (all of her printers) to offline.
    Blocks until the operation is finished."""
    UserOffline_Internal(appKey, host, version, callback).join()

def UserOnline(appKey, host, version, callback):
    """Sets the status of the user (all of her printers) to online."""
    with userDataLock:
        global userData
        userData.status = True
        wthread = ThreadWaiter(callback)
        if userData.GetPrinterCount() == 1:
            thread = NetworkStatusUpdateThread(appKey, host, version, userData.printers[0].id, "on")
            thread.start()
            wthread.add(thread)
        else:
            for printer in userData.GetPrinters():
                thread = NetworkStatusUpdateThread(appKey, host, version, printer.id, StatusToString(printer.IsOn()))
                thread.start()
                wthread.add(thread)
    wthread.start()
