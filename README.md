# Domoticz-Xiaomi-Mi-Air-Purifier-MIoT-Plugin

A Python plugin for [Domoticz](https://www.domoticz.com/) to access Xiaomi Mi Air Purifier 3 / 3 H / Pro H

Note: it does NOT work for Xiaomi Mi Air Purifier 3 C / Pro

Based on the repositories:
* https://github.com/kofec/domoticz-AirPurifier
* https://github.com/rytilahti/python-miio
* https://github.com/Squachen/micloud

## Installation

The instructions shown below are for a "Raspberry Pi 4 Model B" running the "Raspbian GNU/Linux 10 (Debian Buster)" operating system.
However, they should also be fine for another Debian based systems.

Make sure that your [Domoticz](https://www.domoticz.com/) instance supports Python plugins: https://www.domoticz.com/wiki/Using_Python_plugins

Make sure that you have the "`rustc`" compiler (the "`rustc --version`" must be "`1.41.0`" or newer) and its "`cargo`" package manager installed.

```bash
sudo apt-get install rustc cargo
```

Install the required Python packages.

Note: on a "Debian Buster", one cannot install "`python-miio >= 0.5.9`", because it depends on "`cryptography >= 35`", which fails to build on this system. However, this problem does no exist on other (newer) systems (and then, one does not need to explicitly request "`==0.5.8`" below).

```bash
pip3 install -U python-miio==0.5.8 # the last version that uses cryptography 3.4.x
pip3 install -U micloud
```

You can now retrieve informations about your device (the default "[`<language_code_of_the_server>`](https://www.openhab.org/addons/bindings/miio/#country-servers)" is "`de`").

```bash
micloud -u <your_Xiaomi_username> -c <language_code_of_the_server> --pretty # notice the returned "<localip>" and "<token>"
miiocli device --ip <localip> --token <token> info # a simple test that we can directly access it
```

Get the [plugin source code](https://github.com/JacekHoleczek/Domoticz-Xiaomi-Mi-Air-Purifier-MIoT-Plugin) into your [Domoticz](https://www.domoticz.com/) "`plugins`" directory.

```bash
cd YOUR_DOMOTICZ_PATH/plugins # usually "${HOME}/domoticz/plugins"
git clone https://github.com/JacekHoleczek/Domoticz-Xiaomi-Mi-Air-Purifier-MIoT-Plugin
```

Use the "`MyAir.py`" script to verify that everything works.

```bash
cd Domoticz-Xiaomi-Mi-Air-Purifier-MIoT-Plugin
./MyAir.py -h
./MyAir.py --debug <localip> <token>
```

Adjust the "`python-miio`" location in the "`plugin.py`" file.

```bash
PYTHON_MIIO_LOCATION="$(pip3 show python-miio | sed -n -e '{s/^Location: //p}')"
# echo ${PYTHON_MIIO_LOCATION}
sed -i -e '{s#\"PYTHON_MIIO_LOCATION\"#\"'${PYTHON_MIIO_LOCATION}'\"#}' plugin.py
```

Restart the [Domoticz](https://www.domoticz.com/) service and reload the web page, then:
* go to "`Setup`" -> "`Hardware`" and define a new one of the "`Type:` `Xiaomi Mi Air Purifier MIoT`",
* set the "`Name`", the "`Local IP`" (="`<localip>`"), and the "`Token`" (="`<token>`"),
* click the "`Add`" button.

Enjoy your new "`Setup`" -> "`Devices`".

## Update

Get the new [plugin source code](https://github.com/JacekHoleczek/Domoticz-Xiaomi-Mi-Air-Purifier-MIoT-Plugin) into your [Domoticz](https://www.domoticz.com/) "`plugins`" directory.

```bash
cd YOUR_DOMOTICZ_PATH/plugins/Domoticz-Xiaomi-Mi-Air-Purifier-MIoT-Plugin
git reset --hard -q # discard any local changes completely
git pull
```

Adjust the "`python-miio`" location in the "`plugin.py`" file, as shown above.

Restart the [Domoticz](https://www.domoticz.com/) service, e.g.:

```bash
sudo systemctl restart domoticz.service
```

Note: when the [plugin source code](https://github.com/JacekHoleczek/Domoticz-Xiaomi-Mi-Air-Purifier-MIoT-Plugin) changes, you may need to "`Setup`" -> "`Hardware`" -> "`Delete`" your device first, then restart the [Domoticz](https://www.domoticz.com/) service (and reload the web page), and finally "`Setup`" -> "`Hardware`" -> "`Add`" your device again.

## Troubleshooting

In case of problems (e.g., the plugin is not visible in the plugin list), check the "`Setup`" -> "`Log`" and see the [Domoticz Wiki](https://www.domoticz.com/wiki) (e.g., for typical [problems locating Python](http://www.domoticz.com/wiki/Linux#Problems_locating_Python)).

