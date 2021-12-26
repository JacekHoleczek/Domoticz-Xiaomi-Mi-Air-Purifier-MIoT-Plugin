#
# A Python plugin for Domoticz to access Xiaomi Mi Air Purifier 3 / 3 H / Pro H
#
# Note: before using it, make sure you adjust the "site_path" below, e.g:
#  PYTHON_MIIO_LOCATION="$(pip3 show python-miio | sed -n -e '{s/^Location: //p}')"
#  echo ${PYTHON_MIIO_LOCATION}
#  sed -i -e '{s#\"PYTHON_MIIO_LOCATION\"#\"'${PYTHON_MIIO_LOCATION}'\"#}' plugin.py
#
# Authors:
#  - JacekHoleczek
#  - kofec
#  - Carck
#  - l4m3rx
#  - pawcio
#
# v0.0.1 - initial version
#  based on the "Domoticz plugin for Xiaomi AirPurifier 2/2S and Pro" (v0.2.3):
#   https://github.com/kofec/domoticz-AirPurifier
#  note: it uses the "python-miio" library:
#   https://github.com/rytilahti/python-miio
#
# "print(MyAir.status())" oputput for a "Xiaomi Mi Air Purifier 3 H":
#  <AirPurifierMiotStatus aqi=1 average_aqi=3 buzzer=True buzzer_volume=None
#   child_lock=False fan_level=2 favorite_level=1 favorite_rpm=660
#   filter_hours_used=130 filter_life_remaining=96
#   filter_rfid_product_id=0:0:31:31 filter_rfid_tag=80:70:a1:52:6e:17:4
#   filter_type=FilterType.Regular humidity=50 is_on=True led=True
#   led_brightness=LedBrightness.Dim mode=OperationMode.Fan motor_speed=1600
#   power=on purify_volume=15556 temperature=21.9 use_time=467700>
#

"""
<plugin
 key="Xiaomi-Mi-Air-Purifier-MIoT"
 name="Xiaomi Mi Air Purifier MIoT"
 author="Many Authors"
 version="0.0.1"
 wikilink="https://github.com/rytilahti/python-miio"
 externallink="https://github.com/JacekHoleczek/Domoticz-Xiaomi-Mi-Air-Purifier-MIoT-Plugin">
 <params>
  <param field="Address" label="Local IP" width="200px" required="true" default="127.0.0.1"/>
  <param field="Mode1" label="Token" default="" width="400px" required="true"/>
  <param field="Mode3" label="Check every x minutes" width="40px" default="15" required="true"/>
  <param field="Mode6" label="Debug" width="75px">
   <options>
   <option label="True" value="Debug"/>
   <option label="False" value="Normal" default="true"/>
   </options>
  </param>
 </params>
</plugin>
"""

import Domoticz
import sys
import datetime
import socket
import site
import time
import glob

path = ''
# note: "site.getsitepackages()" may not exist in a "virtualenv"
#       see, e.g., https://github.com/pypa/virtualenv/issues/737
if hasattr(site, 'getsitepackages'):
    path = site.getsitepackages()
else:
    from distutils.sysconfig import get_python_lib
    path = get_python_lib()
for i in path:
    sys.path.append(i)

site_path = "PYTHON_MIIO_LOCATION" # note: it needs to be adjusted before usage
# site_path = "/home/pi/.local/lib/python3.7/site-packages"

sys.path.append(site_path)

eggs = [f for f in glob.glob(site_path + "**/*.egg", recursive=False)]
for f in eggs:
    sys.path.append(f)

import threading
import queue

import miio.airpurifier_miot
from miio import Device, DeviceException
from miio.airpurifier_miot import OperationMode
from miio.airpurifier_miot import LedBrightness
from functools import partial

L10N = {
    'pl': {
        "Air Quality Index":
            "Jakość powietrza",
        "Average Air Quality Index":
            "Średnia wartość AQI",
        "Air pollution Level":
            "Zanieczyszczenie powietrza",
        "Temperature":
            "Temperatura",
        "Humidity":
            "Wilgotność",
        "Fan Speed":
            "Prędkość wiatraka",
        "Favorite Fan Level":
            "Ulubiona prędkość wiatraka",
        "Sensor information":
            "Informacje o stacji",
        "Device Unit=%(Unit)d; Name='%(Name)s' already exists":
            "Urządzenie Unit=%(Unit)d; Name='%(Name)s' już istnieje",
        "Creating device Name=%(Name)s; Unit=%(Unit)d; ; TypeName=%(TypeName)s; Used=%(Used)d":
            "Tworzę urządzenie Name=%(Name)s; Unit=%(Unit)d; ; TypeName=%(TypeName)s; Used=%(Used)d",
        "%(Vendor)s - %(Address)s, %(Locality)s<br/>Station founder: %(sensorFounder)s":
            "%(Vendor)s - %(Address)s, %(Locality)s<br/>Sponsor stacji: %(sensorFounder)s",
        "%(Vendor)s - %(Locality)s %(StreetNumber)s<br/>Station founder: %(sensorFounder)s":
            "%(Vendor)s - %(Locality)s %(StreetNumber)s<br/>Sponsor stacji: %(sensorFounder)s",
        "Great air quality":
            "Bardzo dobra jakość powietrza",
        "Good air quality":
            "Dobra jakość powietrza",
        "Average air quality":
            "Przeciętna jakość powietrza",
        "Poor air quality":
            "Słaba jakość powietrza",
        "Bad air quality":
            "Zła jakość powietrza",
        "Really bad air quality":
            "Bardzo zła jakość powietrza",
        "Sensor id (%(sensor_id)d) not exists":
            "Sensor (%(sensor_id)d) nie istnieje",
        "Not authorized":
            "Brak autoryzacji",
        "Starting device update":
            "Rozpoczynanie aktualizacji urządzeń",
        "Update unit=%d; nValue=%d; sValue=%s":
            "Aktualizacja unit=%d; nValue=%d; sValue=%s",
        "Bad air today!":
            "Zła jakość powietrza",
        "Enter correct airly API key - get one on https://developer.airly.eu":
            "Wprowadź poprawny klucz api -  pobierz klucz na stronie https://developer.airly.eu",
        "Awaiting next pool: %s":
            "Oczekiwanie na następne pobranie: %s",
        "Next pool attempt at: %s":
            "Następna próba pobrania: %s",
        "Connection to airly api failed: %s":
            "Połączenie z airly api nie powiodło się: %s",
        "Unrecognized error: %s":
            "Nierozpoznany błąd: %s"
    },
    'en': { }
}

def _(key):
    try:
        return L10N[Settings["Language"]][key]
    except KeyError:
        return key

class UnauthorizedException(Exception):
    def __init__(self, expression, message):
        self.expression = expression
        self.message = message

class SensorNotFoundException(Exception):
    def __init__(self, expression, message):
        self.expression = expression
        self.message = message

class ConnectionErrorException(Exception):
    def __init__(self, expression, message):
        self.expression = expression
        self.message = message

class BasePlugin:
    MyAir = None

    def __init__(self):
        # Consts
        self.version = "0.0.1"

        self.EXCEPTIONS = {
            "SENSOR_NOT_FOUND":     1,
            "UNAUTHORIZED":         2,
        }

        self.debug = False
        self.inProgress = False

        self.UNIT_AQI                   =  1
        self.UNIT_AVERAGE_AQI           =  2
        self.UNIT_BUZZER                =  3
        # self.UNIT_BUZZER_VOLUME         =  4
        self.UNIT_CHILD_LOCK            =  5
        self.UNIT_FAN_LEVEL             =  6
        self.UNIT_FAVORITE_LEVEL        =  7
        # self.UNIT_FAVORITE_RPM          =  8
        self.FILTER_HOURS_USED          =  9
        self.FILTER_LIFE_REMAINING      = 10
        # self.FILTER_RFID_PRODUCT_ID     = 11
        # self.FILTER_RFID_TAG            = 12
        # self.FILTER_TYPE                = 13
        self.UNIT_HUMIDITY              = 14
        # self.UNIT_IS_ON                 = 15
        self.UNIT_LED                   = 16
        self.UNIT_LED_BRIGHTNESS        = 17
        self.UNIT_MODE                  = 18
        self.UNIT_MOTOR_SPEED           = 19
        self.UNIT_POWER                 = 20
        self.UNIT_PURIFY_VOLUME         = 21
        self.UNIT_TEMPERATURE           = 22
        self.UNIT_USE_TIME              = 23
        self.UNIT_AIR_POLLUTION_LEVEL   = 99

        self.nextpoll = datetime.datetime.now()
        self.messageQueue = queue.Queue()
        self.messageThread = threading.Thread(name="QueueThreadPurifier", target=BasePlugin.handleMessage, args=(self,))
        return

    def connectIfNeeded(self):
        for i in range(1, 6):
            try:
                if None == self.MyAir:
                    self.MyAir = miio.airpurifier_miot.AirPurifierMiot(Parameters["Address"], Parameters["Mode1"])
                break;
            except miio.airpurifier_miot.AirPurifierMiotException as e:
                Domoticz.Error("connectIfNeeded: " + str(e))
                self.MyAir = None

    def handleMessage(self):
        Domoticz.Debug("Entering message handler")
        while True:
            try:
                Message = self.messageQueue.get(block=True)
                if Message is None:
                    Domoticz.Debug("Exiting message handler")
                    self.messageQueue.task_done()
                    break

                self.connectIfNeeded()

                if (Message["Type"] == "onHeartbeat"):
                    self.onHeartbeatInternal(Message["Fetch"])
                elif (Message["Type"] == "onCommand"):
                    self.onCommandInternal(Message["Mthd"], *Message["Arg"])

                self.messageQueue.task_done()

            except Exception as err:
                Domoticz.Error("handleMessage: "+str(err))
                self.MyAir = None
                with self.messageQueue.mutex:
                   	self.messageQueue.queue.clear()

    def onStart(self):
        #Domoticz.Log("path: " + str(sys.path))
        Domoticz.Debug("onStart called")
        if Parameters["Mode6"] == 'Debug':
            self.debug = True
            Domoticz.Debugging(1)
            DumpConfigToLog()
        else:
            Domoticz.Debugging(0)

        self.connectIfNeeded()
        self.MyAir._timeout = 1
        self.messageThread.start()

        Domoticz.Heartbeat(20)
        self.pollinterval = int(Parameters["Mode3"]) * 60

        res = self.MyAir.status()
        Domoticz.Log(str(res))

        # https://www.domoticz.com/wiki/Developing_a_Python_plugin#Available_Device_Types
        self.variables = {
            self.UNIT_AQI: {
                "Name":       _("AQI"),
                "TypeName":   "Custom", # "Custom Sensor"
                "Image":      7,
                "Options":    {"Custom": "1;%s" % "AQI"},
                "Used":       1,
                "nValue":     0,
                "sValue":     None,
            },
            self.UNIT_AVERAGE_AQI: {
                "Name":       _("Average AQI"),
                "TypeName":   "Custom", # "Custom Sensor"
                "Image":      7,
                "Options":    {"Custom": "1;%s" % "AQI"},
                "Used":       0,
                "nValue":     0,
                "sValue":     None,
            },
            self.UNIT_BUZZER: {
                "Name":       _("Buzzer"),
                "TypeName":   "Switch", # On/Off
                "Image":      7,
                "Used":       0,
                "nValue":     0,
                "sValue":     None,
            },
            # self.UNIT_BUZZER_VOLUME: {},
            self.UNIT_CHILD_LOCK: {
                "Name":       _("Child Lock"),
                "TypeName":   "Switch", # On/Off
                "Image":      7,
                "Used":       1,
                "nValue":     0,
                "sValue":     None,
            },
            self.UNIT_FAN_LEVEL: {
                "Name":       _("Fan Level"),
                "TypeName":   "Selector Switch",
                "Switchtype": 18, # "Selector"
                "Image":      7,
                "Options":    {"LevelActions": "||",
                               "LevelNames": "1|2|3",
                               "LevelOffHidden": "false",
                               "SelectorStyle": "0"},
                "Used":       1,
                "nValue":     0,
                "sValue":     None,
            },
            self.UNIT_FAVORITE_LEVEL: {
                "Name":       _("Favorite Level"),
                "TypeName":   "Selector Switch",
                "Switchtype": 18, # "Selector"
                "Image":      7,
                "Options":    {"LevelActions": "||||||||||||||",
                               "LevelNames": "0|1|2|3|4|5|6|7|8|9|10|11|12|13|14",
                               "LevelOffHidden": "false",
                               "SelectorStyle": "1"},
                "Used":       1,
                "nValue":     0,
                "sValue":     None,
            },
            # self.UNIT_FAVORITE_RPM: {},
            self.FILTER_HOURS_USED: {
                "Name":       _("Filter Hours Used"),
                "TypeName":   "Custom", # "Custom Sensor"
                "Image":      7,
                "Options":    {"Custom": "1;%s" % "h"},
                "Used":       0,
                "nValue":     0,
                "sValue":     None,
            },
            self.FILTER_LIFE_REMAINING: {
                "Name":       _("Filter Life Remaining"),
                "TypeName":   "Custom", # "Custom Sensor"
                "Image":      7,
                "Options":    {"Custom": "1;%s" % "%"},
                "Used":       0,
                "nValue":     0,
                "sValue":     None,
            },
            # self.FILTER_RFID_PRODUCT_ID: {},
            # self.FILTER_RFID_TAG: {},
            # self.FILTER_TYPE: {},
            self.UNIT_HUMIDITY: {
                "Name":       _("Humidity"),
                "TypeName":   "Humidity",
                "Used":       1,
                "nValue":     0,
                "sValue":     None,
            },
            # self.UNIT_IS_ON: {},
            self.UNIT_LED: {
                "Name":       _("Led"),
                "TypeName":   "Switch", # On/Off
                "Image":      7,
                "Used":       0,
                "nValue":     0,
                "sValue":     None,
            },
            self.UNIT_LED_BRIGHTNESS: {
                "Name":       _("Led Brightness"),
                "TypeName":   "Selector Switch",
                "Switchtype": 18, # "Selector"
                "Image":      7,
                "Options":    {"LevelActions": "||",
                               "LevelNames": "Off|Dim|Bright",
                               "LevelOffHidden": "false",
                               "SelectorStyle": "0"},
                "Used":       1,
                "nValue":     0,
                "sValue":     None,
            },
            self.UNIT_MODE: {
                "Name":       _("Mode"),
                "TypeName":   "Selector Switch",
                "Switchtype": 18, # "Selector"
                "Image":      7,
                "Options":    {"LevelActions": "|||",
                               # "LevelNames": "Auto|Silent|Favorite|Fan",
                               "LevelNames": "Auto|Night|Fave|123",
                               "LevelOffHidden": "false",
                               "SelectorStyle": "0"},
                "Used":       1,
                "nValue":     0,
                "sValue":     None,
            },
            self.UNIT_MOTOR_SPEED: {
                "Name":       _("Motor Speed"),
                "TypeName":   "Custom", # "Custom Sensor"
                "Image":      7,
                "Options":    {"Custom": "1;%s" % "RPM"},
                "Used":       0,
                "nValue":     0,
                "sValue":     None,
            },
            self.UNIT_POWER: {
                "Name":       _("Power"),
                "TypeName":   "Switch", # On/Off
                "Image":      7,
                "Used":       1,
                "nValue":     0,
                "sValue":     None,
            },
            self.UNIT_PURIFY_VOLUME: {
                "Name":       _("Purify Volume"),
                "TypeName":   "Custom", # "Custom Sensor"
                "Image":      7,
                "Options":    {"Custom": "1;%s" % "m^3"},
                "Used":       0,
                "nValue":     0,
                "sValue":     None,
            },
            self.UNIT_TEMPERATURE: {
                "Name":       _("Temperature"),
                "TypeName":   "Temperature",
                "Used":       1,
                "nValue":     0,
                "sValue":     None,
            },
            self.UNIT_USE_TIME: {
                "Name":       _("Use Time"),
                "TypeName":   "Custom", # "Custom Sensor"
                "Image":      7,
                "Options":    {"Custom": "1;%s" % "s"},
                "Used":       0,
                "nValue":     0,
                "sValue":     None,
            },
            self.UNIT_AIR_POLLUTION_LEVEL: {
                "Name":       _("Air Pollution Level"),
                "TypeName":   "Alert",
                "Image":      7,
                "Used":       0,
                "nValue":     0,
                "sValue":     None,
            },
        }

        self.createDevice() # create all devices

        self.onHeartbeat(fetch=False)

    def onStop(self):
        Domoticz.Log("onStop called")

        with self.messageQueue.mutex:
            self.messageQueue.queue.clear()

        # signal queue thread to exit
        self.messageQueue.put(None)
        Domoticz.Log("Clearing message queue ...")
        self.messageQueue.join()

        # Wait until queue thread has exited
        Domoticz.Log("Threads still active: "+str(threading.active_count())+", should be 1.")
        while (threading.active_count() > 1):
            for thread in threading.enumerate():
                if (thread.name != threading.current_thread().name):
                    Domoticz.Log("'"+thread.name+"' is still running, waiting otherwise Domoticz will abort on plugin exit.")
            time.sleep(1.0)

        Domoticz.Debugging(0)

    def onConnect(self, Status, Description):
        Domoticz.Log("onConnect called")

    def onMessage(self, Data, Status, Extra):
        Domoticz.Log("onMessage called")

    def onCommandInternal(self, func, *arg):
        try:
            stat = func(*arg)
            Domoticz.Log(str(stat))

            self.onHeartbeat(fetch=True)
        except miio.airpurifier_miot.AirPurifierMiotException as e:
            Domoticz.Log("Something fail: " + e.output.decode())
            self.onHeartbeat(fetch=False)
        except Exception as e:
            Domoticz.Error(_("Unrecognized command error: %s") % str(e))

    def onCommand(self, Unit, Command, Level, Hue):
        Domoticz.Log("onCommand called for Unit " + str(Unit) + ": Parameter '" + str(Command) + "', Level: " + str(Level))
        # self.messageQueue.put({"Type": "Command", "Unit": Unit, "Command": Command, "Level": Level, "Hue": Hue})

        mthd = None
        arg = []

        if Unit == self.UNIT_BUZZER: # ... self.UNIT_BUZZER ...
            mthd = self.MyAir.set_buzzer
            arg = [True if str(Command).upper() == "TRUE" or str(Command).upper() == "ON" else False]
        elif Unit == self.UNIT_CHILD_LOCK: # ... self.UNIT_CHILD_LOCK ...
            mthd = self.MyAir.set_child_lock
            arg = [True if str(Command).upper() == "TRUE" or str(Command).upper() == "ON" else False]
        elif Unit == self.UNIT_FAN_LEVEL: # ... self.UNIT_FAN_LEVEL ...
            mthd = self.MyAir.set_fan_level
            arg = [int(int(Level)/10 + 1)] # 1 ... 3
        elif Unit == self.UNIT_FAVORITE_LEVEL: # ... self.UNIT_FAVORITE_LEVEL ...
            mthd = self.MyAir.set_favorite_level
            arg = [int(int(Level)/10)] # 0 ... 14
        elif Unit == self.UNIT_LED: # ... self.UNIT_LED ...
            mthd = self.MyAir.set_led
            arg = [True if str(Command).upper() == "TRUE" or str(Command).upper() == "ON" else False]
        elif Unit == self.UNIT_LED_BRIGHTNESS and int(Level) == 0: # ... self.UNIT_LED_BRIGHTNESS ...
            mthd = self.MyAir.set_led_brightness
            arg = [LedBrightness.Off]
        elif Unit == self.UNIT_LED_BRIGHTNESS and int(Level) == 10:
            mthd = self.MyAir.set_led_brightness
            arg = [LedBrightness.Dim]
        elif Unit == self.UNIT_LED_BRIGHTNESS and int(Level) == 20:
            mthd = self.MyAir.set_led_brightness
            arg = [LedBrightness.Bright]
        elif Unit == self.UNIT_MODE and int(Level) == 0: # ... self.UNIT_MODE ...
            mthd = self.MyAir.set_mode
            arg = [OperationMode.Auto]
        elif Unit == self.UNIT_MODE and int(Level) == 10:
            mthd = self.MyAir.set_mode
            arg = [OperationMode.Silent]
        elif Unit == self.UNIT_MODE and int(Level) == 20:
            mthd = self.MyAir.set_mode
            arg = [OperationMode.Favorite]
        elif Unit == self.UNIT_MODE and int(Level) == 30:
            mthd = self.MyAir.set_mode
            arg = [OperationMode.Fan]
        elif Unit == self.UNIT_POWER: # ... self.UNIT_POWER ...
            mthd = self.MyAir.on if str(Command).upper() == "TRUE" or str(Command).upper() == "ON" else self.MyAir.off
        else:
            Domoticz.Log("onCommand call not found")
            return

        Domoticz.Log(str({"Type":"onCommand", "Mthd":mthd, "Arg":arg}))
        self.messageQueue.put({"Type":"onCommand", "Mthd":mthd, "Arg":arg})

    def onNotification(self, Name, Subject, Text, Status, Priority, Sound, ImageFile):
        Domoticz.Log("Notification: " + Name + "," + Subject + "," + Text + "," + Status + "," + str(
            Priority) + "," + Sound + "," + ImageFile)

    def onDisconnect(self):
        Domoticz.Log("onDisconnect called")

    def postponeNextPool(self, seconds=3600):
        self.nextpoll = (datetime.datetime.now() + datetime.timedelta(seconds=seconds))
        return self.nextpoll

    def createDevice(self, key=None):
        """create Domoticz virtual device"""

        def createSingleDevice(key):
            """inner helper function to handle device creation"""

            item = self.variables[key]
            _name = item['Name']
            _unit = key

            # skip if already exists
            if key in Devices:
                Domoticz.Debug(_("Device Unit=%(Unit)d; Name='%(Name)s' already exists") % {'Unit': key, 'Name': _name})
                return

            _typename = item['TypeName']

            try:
                _switchtype = item['Switchtype']
            except KeyError:
                _switchtype = 0

            try:
                _image = item['Image']
            except KeyError:
                _image = 0

            try:
                _options = item['Options']
            except KeyError:
                _options = {}

            try:
                _used = item['Used']
            except KeyError:
                _used = 0

            Domoticz.Debug(_("Creating device Name=%(Name)s; Unit=%(Unit)d; ; TypeName=%(TypeName)s; Used=%(Used)d") % {
                               'Name':     _name,
                               'Unit':     _unit,
                               'TypeName': _typename,
                               'Used':     _used,
                           })

            Domoticz.Device(
                Name=_name,
                Unit=_unit,
                TypeName=_typename,
                Switchtype=_switchtype,
                Image=_image,
                Options=_options,
                Used=_used
            ).Create()

        if key:
            createSingleDevice(key)
        else:
            for k in self.variables.keys():
                createSingleDevice(k)

    def onHeartbeat(self, fetch=False):
        Domoticz.Debug("onHeartbeat called")
        self.messageQueue.put({"Type": "onHeartbeat", "Fetch": fetch})
        return True

    def onHeartbeatInternal(self, fetch=False):
        now = datetime.datetime.now()
        if fetch == False:
            if now < self.nextpoll:
                Domoticz.Debug(_("Awaiting next pool: %s") % str(self.nextpoll))
                return

        # Set next pool time
        self.postponeNextPool(seconds=self.pollinterval)

        try:
            res = self.MyAir.status()
            Domoticz.Log(str(res))
            # check if another thread is not running
            # and time between last fetch has elapsed
            self.inProgress = True

            # ... self.UNIT_AQI ...
            try:
                self.variables[self.UNIT_AQI]['nValue'] = res.aqi
                self.variables[self.UNIT_AQI]['sValue'] = str(res.aqi)
            except KeyError:
                pass  # No aqi

            # ... self.UNIT_AVERAGE_AQI ...
            try:
                self.variables[self.UNIT_AVERAGE_AQI]['nValue'] = res.average_aqi
                self.variables[self.UNIT_AVERAGE_AQI]['sValue'] = str(res.average_aqi)
            except KeyError:
                pass  # No average_aqi

            # ... self.UNIT_BUZZER ...
            if res.buzzer:
                UpdateDevice(self.UNIT_BUZZER, 1, "Buzzer ON")
            else:
                UpdateDevice(self.UNIT_BUZZER, 0, "Buzzer OFF")

            # ... self.UNIT_BUZZER_VOLUME ...

            # ... self.UNIT_CHILD_LOCK ...
            if res.child_lock:
                UpdateDevice(self.UNIT_CHILD_LOCK, 1, "Child Lock ON")
            else:
                UpdateDevice(self.UNIT_CHILD_LOCK, 0, "Child Lock OFF")

            # ... self.UNIT_FAN_LEVEL ...
            UpdateDevice(self.UNIT_FAN_LEVEL, 1, str(int(int(res.fan_level)-1)*10))

            # ... self.UNIT_FAVORITE_LEVEL ...
            UpdateDevice(self.UNIT_FAVORITE_LEVEL, 1, str(int(res.favorite_level)*10))

            # ... self.UNIT_FAVORITE_RPM ...

            # ... self.FILTER_HOURS_USED ...
            try:
                self.variables[self.FILTER_HOURS_USED]['nValue'] = res.filter_hours_used
                self.variables[self.FILTER_HOURS_USED]['sValue'] = str(res.filter_hours_used)
            except KeyError:
                pass  # No filter_hours_used

            # ... self.FILTER_LIFE_REMAINING ...
            try:
                self.variables[self.FILTER_LIFE_REMAINING]['nValue'] = res.filter_life_remaining
                self.variables[self.FILTER_LIFE_REMAINING]['sValue'] = str(res.filter_life_remaining)
            except KeyError:
                pass  # No filter_life_remaining

            # ... self.FILTER_RFID_PRODUCT_ID ...

            # ... self.FILTER_RFID_TAG ...

            # ... self.FILTER_TYPE ...

            # ... self.UNIT_HUMIDITY ...
            try:
                humidity = int(round(res.humidity))
                if humidity < 40:
                    humidity_status = 2  # dry humidity
                elif 40 <= humidity <= 60:
                    humidity_status = 0  # normal humidity
                elif 40 < humidity <= 70:
                    humidity_status = 1  # comfortable humidity
                else:
                    humidity_status = 3  # wet humidity
                #
                self.variables[self.UNIT_HUMIDITY]['nValue'] = humidity
                self.variables[self.UNIT_HUMIDITY]['sValue'] = str(humidity_status)
                #
            except KeyError:
                pass  # No humidity

            # ... self.UNIT_IS_ON ...

            # ... self.UNIT_LED ...
            try:
                if bool(res.led):
                    UpdateDevice(self.UNIT_LED, 1, "Led ON")
                else:
                    UpdateDevice(self.UNIT_LED, 0, "Led OFF")
            except KeyError:
                pass  # No led

            # ... self.UNIT_LED_BRIGHTNESS ...
            try:
                if str(res.led_brightness) == "LedBrightness.Off":
                    UpdateDevice(self.UNIT_LED_BRIGHTNESS, 0, '0')
                elif str(res.led_brightness) == "LedBrightness.Dim":
                    UpdateDevice(self.UNIT_LED_BRIGHTNESS, 10, '10')
                elif str(res.led_brightness) == "LedBrightness.Bright":
                    UpdateDevice(self.UNIT_LED_BRIGHTNESS, 20, '20')
                else:
                    Domoticz.Log("Wrong state for UNIT_LED_BRIGHTNESS: " + str(res.led_brightness))
            except KeyError:
                Domoticz.Log("Cannot update: UNIT_LED_BRIGHTNESS")
                pass  # No led_brightness

            # ... self.UNIT_MODE ...
            try:
                if str(res.mode) == "OperationMode.Unknown":
                    UpdateDevice(self.UNIT_MODE, -10, '-10')
                elif str(res.mode) == "OperationMode.Auto":
                    UpdateDevice(self.UNIT_MODE, 0, '0')
                elif str(res.mode) == "OperationMode.Silent":
                    UpdateDevice(self.UNIT_MODE, 10, '10')
                elif str(res.mode) == "OperationMode.Favorite":
                    UpdateDevice(self.UNIT_MODE, 20, '20')
                elif str(res.mode) == "OperationMode.Fan":
                    UpdateDevice(self.UNIT_MODE, 30, '30')
                else:
                    Domoticz.Log("Wrong state for UNIT_MODE: " + str(res.mode))
            except KeyError:
                Domoticz.Log("Cannot update: UNIT_MODE")
                pass  # No mode

            # ... self.UNIT_MOTOR_SPEED ...
            try:
                self.variables[self.UNIT_MOTOR_SPEED]['nValue'] = res.motor_speed
                self.variables[self.UNIT_MOTOR_SPEED]['sValue'] = str(res.motor_speed)
            except KeyError:
                pass  # No motor_speed

            # ... self.UNIT_POWER ...
            try:
                if str(res.power).upper() == "ON":
                    UpdateDevice(self.UNIT_POWER, 1, "AirPurifier ON")
                elif str(res.power).upper() == "OFF":
                    UpdateDevice(self.UNIT_POWER, 0, "AirPurifier OFF")
            except KeyError:
                pass  # No power

            # ... self.UNIT_PURIFY_VOLUME ...
            try:
                self.variables[self.UNIT_PURIFY_VOLUME]['nValue'] = res.purify_volume
                self.variables[self.UNIT_PURIFY_VOLUME]['sValue'] = str(res.purify_volume)
            except KeyError:
                pass  # No purify_volume

            # ... self.UNIT_TEMPERATURE ...
            try:
                self.variables[self.UNIT_TEMPERATURE]['nValue'] = int(round(res.temperature))
                self.variables[self.UNIT_TEMPERATURE]['sValue'] = str(res.temperature)
            except KeyError:
                pass  # No temperature

            # ... self.UNIT_USE_TIME ...
            try:
                self.variables[self.UNIT_USE_TIME]['nValue'] = res.use_time
                self.variables[self.UNIT_USE_TIME]['sValue'] = str(res.use_time)
            except KeyError:
                pass  # No use_time

            # ... self.UNIT_AIR_POLLUTION_LEVEL ...
            #
            # Air Pollution Level
            #
            #   0–50  Excellent
            #  51–100 Good
            # 101–150 Lightly Polluted
            # 151–200 Moderately Polluted
            # 201–300 Heavily Polluted
            # 300+    Severely Polluted
            #
            # https://en.wikipedia.org/wiki/Air_quality_index
            #
            pollutionLevel = int(self.variables[self.UNIT_AQI]['sValue'])
            # sometimes response has 10 times lower value - uncomment below
            # pollutionLevel = pollutionLevel * 10
            if pollutionLevel < 50:
                pollutionLevel = 1  # green
                pollutionText = _("Great air quality")
            elif pollutionLevel < 100:
                pollutionLevel = 1  # green
                pollutionText = _("Good air quality")
            elif pollutionLevel < 150:
                pollutionLevel = 2  # yellow
                pollutionText = _("Average air quality")
            elif pollutionLevel < 200:
                pollutionLevel = 3  # orange
                pollutionText = _("Poor air quality")
            elif pollutionLevel < 300:
                pollutionLevel = 4  # red
                pollutionText = _("Bad air quality")
            elif pollutionLevel >= 300:
                pollutionLevel = 4  # red
                pollutionText = _("Really bad air quality")
            else:
                pollutionLevel = 0
                pollutionText = _("Unknown")
            #
            self.variables[self.UNIT_AIR_POLLUTION_LEVEL]['nValue'] = pollutionLevel
            self.variables[self.UNIT_AIR_POLLUTION_LEVEL]['sValue'] = pollutionText

            self.doUpdate()

        except miio.airpurifier_miot.AirPurifierMiotException as e:
            Domoticz.Error("onHeartbeatInternal: " + str(e))
            self.MyAir = None
            return
        except Exception as e:
            Domoticz.Error(_("Unrecognized heartbeat error: %s") % str(e))
        finally:
            self.inProgress = False
        if Parameters["Mode6"] == 'Debug':
            Domoticz.Debug("onHeartbeat finished")

    def doUpdate(self):
        Domoticz.Log(_("Starting device update"))
        for unit in self.variables:
            Domoticz.Debug(str(self.variables[unit]))
            nV = self.variables[unit]['nValue']
            sV = self.variables[unit]['sValue']

            # cast float to str
            if isinstance(sV, float):
                sV = str(float("{0:.1f}".format(sV))).replace('.', ',')

            # Create device if required
            if sV:
                self.createDevice(key=unit)
                if unit in Devices:
                    Domoticz.Log(_("Update unit=%d; nValue=%d; sValue=%s") % (unit, nV, sV))
                    Devices[unit].Update(nValue=nV, sValue=sV)

global _plugin
_plugin = BasePlugin()

def onStart():
    global _plugin
    _plugin.onStart()

def onStop():
    global _plugin
    _plugin.onStop()

def onConnect(Status, Description):
    global _plugin
    _plugin.onConnect(Status, Description)

def onMessage(Data, Status, Extra):
    global _plugin
    _plugin.onMessage(Data, Status, Extra)

def onCommand(Unit, Command, Level, Hue):
    global _plugin
    _plugin.onCommand(Unit, Command, Level, Hue)

def onNotification(Name, Subject, Text, Status, Priority, Sound, ImageFile):
    global _plugin
    _plugin.onNotification(Name, Subject, Text, Status, Priority, Sound, ImageFile)

def onDisconnect():
    global _plugin
    _plugin.onDisconnect()

def onHeartbeat():
    global _plugin
    _plugin.onHeartbeat()

    # Generic helper functions
def DumpConfigToLog():
    for x in Parameters:
        if Parameters[x] != "":
            Domoticz.Debug( "'" + x + "':'" + str(Parameters[x]) + "'")
    Domoticz.Debug("Device count: " + str(len(Devices)))
    for x in Devices:
        Domoticz.Debug("Device:           " + str(x) + " - " + str(Devices[x]))
        Domoticz.Debug("Device ID:       '" + str(Devices[x].ID) + "'")
        Domoticz.Debug("Device Name:     '" + Devices[x].Name + "'")
        Domoticz.Debug("Device nValue:    " + str(Devices[x].nValue))
        Domoticz.Debug("Device sValue:   '" + Devices[x].sValue + "'")
        Domoticz.Debug("Device LastLevel: " + str(Devices[x].LastLevel))
    return

def UpdateDevice(Unit, nValue, sValue):
    # Make sure that the Domoticz device still exists (they can be deleted) before updating it
    if (Unit in Devices):
        if (Devices[Unit].nValue != nValue) or (Devices[Unit].sValue != sValue):
            Devices[Unit].Update(nValue=nValue, sValue=str(sValue))
            Domoticz.Log("Update " + str(nValue) + ":'" + str(sValue) + "' (" + Devices[Unit].Name + ")")
    return

