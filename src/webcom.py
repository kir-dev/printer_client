# encoding: utf-8

from printer import *
import urllib
import urllib2
#import urllib.parse
#import urllib.request
import codecs
import errors

class Connection:
    """
    Sends the params to the server, and returns the results.
    Both the sent and returned params are key/value pairs.
    """
    def __init__(self, host):
        self.host = host
        self.sendParams = dict()

    def AddParam(self, key, value):
        self.sendParams[key] = value

    def __Send(self):
        data = urllib.urlencode(self.sendParams)

        return urllib2.urlopen(self.host, data)

    def GetResults(self):
        """
        Connects to the server, sends the params added with AddParam,
        and returns the results as a dict.
        """
        receivedDict = {}
        for s in codecs.iterdecode(self.__Send(), "utf-8"):
            kv = s.split("=")
            key = kv[0]
            val = "".join(kv[1:]).strip()
            receivedDict[key] = val

        if "error" in receivedDict:
            raise Exception, receivedDict["error"]

        if "special" in receivedDict:
            if receivedDict["special"] == "update":
                raise errors.UpdateError(False)
            else:
                raise Exception, "Nem támogatott speciális utatsítás"

        return receivedDict

def GetUserData(appkey, host, version):
    """Fetches a user's data from a remote server"""
    c = Connection(host)
    c.AddParam("appkey", appkey)
    c.AddParam("version", version)
    data = c.GetResults()

    i = 0
    def Status(id): return "printer_%d_status" % id
    def Id(id): return "printer_%d_id" % id
    def Name(id): return "printer_%d_name" % id

    user = User(data["name"])

    while Status(i) in data:
        user.AddPrinter(Printer(data[Id(i)], data[Name(i)], data[Status(i)]))
        i += 1

    return user

def SetPrinterStatus(appkey, host, version, printerID, newStatus):
    """Set's the status of a specific printer."""
    c = Connection(host)
    c.AddParam("appkey", appkey)
    c.AddParam("printer", printerID)
    c.AddParam("status", newStatus)
    c.AddParam("version", version)

    data = c.GetResults()

    if data["status"] != newStatus:
        raise Exception, "Ismeretlen hiba"


