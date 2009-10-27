# encoding: utf-8

import errors

class User(object):
    """
    State object of the application: stores the name, printers,
    user's status and errors.
    """
    def __init__(self, name="None", initialized=True):
        self.error = None
        self.requiredUpdate = False
        self.initialized = initialized
        self.name = name
        self.printers = list()
        self.status = True

    def CopyFrom(self, other):
        """Clones the the target object"""
        self.error = other.error
        self.requiredUpdate = other.requiredUpdate
        self.initialized = other.initialized
        self.name = other.name
        self.printers = other.printers
        self.status = other.status

    def AddPrinter(self, printer):
        self.printers.append(printer)

    def __str__(self):
        return 'User "%s" having %d printer(s)' % (self.name, len(self.printers))

    def GetPrinter(self, index):
        return self.printers[index]

    def GetPrinterFromId(self, id):
        for p in self.printers:
            if p.id == id:
                return p
        raise errors.UnknownError, "Hibás nyomtató-azonosító"

    def GetPrinters(self):
        return self.printers.__iter__()

    def GetPrinterCount(self):
        return len(self.printers)

class Printer(object):
    """Represents one printer"""
    def __init__(self, id, name, status):
        self.id = id
        self.name = name
        self.status = status

    def IsOn(self):
        return self.status == "on"

    def __str__(self):
        return 'Printer "%s", id="%s", status=%s' % (self.name, self.id, self.status)

