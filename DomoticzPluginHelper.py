"""Domoticz Plugin helper.
Contains commonly used functions and plugin boilerplate code.

Author: gaelj

Based on Smart Virtual Thermostat python plugin for Domoticz (Author: Logread, adapted from the Vera plugin by Antor)
"""

from enum import Enum, IntEnum
from typing import List, Dict
import json
import urllib.parse as parse
import urllib.request as request
from datetime import datetime, timedelta
import time
import base64
import itertools
from distutils.version import LooseVersion


from DomoticzWrapperClass import \
    DomoticzTypeName, DomoticzDebugLevel, DomoticzPluginParameters, \
    DomoticzWrapper, DomoticzDevice, DomoticzConnection, DomoticzImage, \
    DomoticzDeviceTypes


class DomoticzPluginHelper:
    def __init__(self, _d: DomoticzWrapper, _internalsDefaults):
        self.d = _d

        # internal configuration
        self.debug = False
        self.logLevel = "Verbose"
        self.statusSupported = True
        self.InternalsDefaults = _internalsDefaults
        self.Internals = self.InternalsDefaults.copy()

    def onStart(self):
        self.d.Debugging([DomoticzDebugLevel.ShowAll])
        self.DumpConfigToLog()

    def onStop(self):
        self.d.Debugging([DomoticzDebugLevel.ShowNone])

    def onConnect(self, Connection, Status, Description):
        self.d.Log("onConnect called")

    def onMessage(self, Connection, Data):
        self.d.Log("onMessage called")

    def onCommand(self, Unit, Command, Level, Color):
        self.d.Debug("onCommand called for Unit {}: Command '{}', Level: {}".format(
            Unit, Command, Level))

    def onNotification(self, Name, Subject, Text, Status, Priority, Sound, ImageFile):
        self.d.Log("Notification: " + Name + "," + Subject + "," + Text +
                   "," + Status + "," + str(Priority) + "," + Sound + "," + ImageFile)

    def onDisconnect(self, Connection):
        self.d.Log("onDisconnect called")

    def onHeartbeat(self):
        pass

    def DomoticzAPI(self, APICall: str):
        resultJson = None
        url = "http://{}:{}/json.htm?{}".format(
            self.d.Parameters.Address, self.d.Parameters.Port, parse.quote(APICall, safe="&="))
        self.d.Debug("Calling domoticz API: {}".format(url))
        try:
            req = request.Request(url)
            if self.d.Parameters.Username != "":
                self.d.Debug("Add authentication for user {}".format(
                    self.d.Parameters.Username))
                credentials = ('%s:%s' %
                               (self.d.Parameters.Username, self.d.Parameters.Password))
                encoded_credentials = base64.b64encode(
                    credentials.encode('ascii'))
                req.add_header('Authorization', 'Basic %s' %
                               encoded_credentials.decode("ascii"))

            response = request.urlopen(req)
            if response.status == 200:
                resultJson = json.loads(response.read().decode('utf-8'))
                if resultJson["status"] != "OK":
                    self.d.Error("Domoticz API returned an error: status = {}".format(
                        resultJson["status"]))
                    resultJson = None
            else:
                self.d.Error(
                    "Domoticz API: http error = {}".format(response.status))
        except:
            self.d.Error("Error calling '{}'".format(url))
        return resultJson

    def CheckParam(self, name: str, value, default: int):
        """Check that the value is an integer. If not, log an error and use the default value

        Arguments:
            name {str} -- The name to log
            value {any} -- The value to check
            default {int} -- Default value to use in case of error

        Returns:
            int -- The value if int or default value
        """
        try:
            param = int(value)
        except ValueError:
            param = default
            self.d.Error("Parameter '{}' has an invalid value of '{}' ! default of '{}' is instead used.".format(
                name, value, default))
        return param

    def DumpConfigToLog(self):
        self.d.Debug("***** Start plugin config *****")
        for x in self.d.ParametersDict:
            parameter = self.d.ParametersDict[x]
            if parameter != "":
                self.d.Debug("'" + x + "':'" + str(parameter) + "'")
        self.d.Debug("Device count: " + str(len(self.d.Devices)))
        for x in self.d.Devices:
            device = self.d.Devices[x]
            self.d.Debug("Device:           " +
                         str(x.name) + " - " + str(device))
            self.d.Debug("Device ID:       '" + str(device.ID) + "'")
            self.d.Debug("Device Name:     '" + device.Name + "'")
            self.d.Debug("Device nValue:    " + str(device.nValue))
            self.d.Debug("Device sValue:   '" + device.sValue + "'")
            self.d.Debug("Device LastLevel: " + str(device.LastLevel))
        self.d.Debug("***** End plugin config *****")
        return

    def GetUserVar(self):
        variables = self.DomoticzAPI("type=command&param=getuservariables")
        if variables:
            # there is a valid response from the API but we do not know if our variable exists yet
            noVar = True
            varname = self.d.Parameters.Name + \
                "-InternalVariables"
            valuestring = ""
            if "result" in variables:
                for variable in variables["result"]:
                    if variable["Name"] == varname:
                        valuestring = variable["Value"]
                        noVar = False
                        break
            if noVar:
                # create user variable since it does not exist
                self.WriteLog("User Variable {} does not exist. Creation requested".format(
                    varname), "Verbose")

                # check for Domoticz version:
                # there is a breaking change on dzvents_version 2.4.9, API was changed from 'saveuservariable' to 'adduservariable'
                # using 'saveuservariable' on latest versions returns a "status = 'ERR'" error

                # get a status of the actual running Domoticz instance, set the parameter accordigly
                parameter = "saveuservariable"
                domoticzInfo = self.DomoticzAPI(
                    "type=command&param=getversion")
                if domoticzInfo is None:
                    self.d.Error(
                        "Unable to fetch Domoticz info... unable to determine version")
                else:
                    if domoticzInfo and LooseVersion(domoticzInfo["dzvents_version"]) >= LooseVersion("2.4.9"):
                        self.WriteLog(
                            "Use 'adduservariable' instead of 'saveuservariable'", "Verbose")
                        parameter = "adduservariable"

                # actually calling Domoticz API
                self.DomoticzAPI("type=command&param={}&vname={}&vtype=2&vvalue={}".format(
                    parameter, varname, str(self.InternalsDefaults)))

                # we re-initialize the internal variables
                self.Internals = self.InternalsDefaults.copy()
            else:
                try:
                    self.Internals.update(eval(valuestring))
                except:
                    self.Internals = self.InternalsDefaults.copy()
                return
        else:
            self.d.Error(
                "Cannot read the uservariable holding the persistent variables")
            self.Internals = self.InternalsDefaults.copy()

    def SaveUserVar(self):
        varname = self.d.Parameters.Name + \
            "-InternalVariables"
        self.DomoticzAPI("type=command&param=updateuservariable&vname={}&vtype=2&vvalue={}".format(
            varname, str(self.Internals)))

    def WriteLog(self, message, level="Normal"):
        if (self.logLevel == "Verbose" and level == "Verbose") or level == "Status":
            if self.statusSupported and level == "Status":
                self.Status(message)
            else:
                self.Log(message)
        elif level == "Normal":
            self.Log(message)

    def InitDevice(self, Name: str, Unit: int,
                   DeviceType: DomoticzDeviceType,
                   Image: int = None,
                   Options: Dict[str, str] = None,
                   Used: bool = False,
                   defaultNValue: float = float(0),
                   defaultSValue: str = ""):
        """Called for each device during onStart. Creates devices if needed"""
        if Unit not in self.d.Devices:
            DomoticzDevice(self.d, Name=Name, Unit=Unit, DeviceType=DeviceType,
                           Image=Image, Options=Options, Used=Used).Create()
            self.d.Devices[Unit].Update(
                nValue=defaultNValue, sValue=defaultSValue)


class DeviceParam:
    """The string and numeric values, and unit name of a measurement"""

    def __init__(self, unit: int, nValue, sValue: str):
        self.unit = unit
        self.nValue = nValue
        self.sValue = sValue


def ParseCSV(strCSV: str):
    listValues = []
    for value in strCSV.split(","):
        try:
            val = int(value.strip())
        except:
            pass
        else:
            listValues.append(val)
    return listValues
