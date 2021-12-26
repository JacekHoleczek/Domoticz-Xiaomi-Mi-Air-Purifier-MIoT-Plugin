#!/usr/bin/env python3

import sys
import argparse
import site

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

import miio.airpurifier_miot

parser = argparse.ArgumentParser(description='This script talks to Xiaomi Mi Air Purifier 3 / 3 H / Pro H')
parser.add_argument('--debug', action='store_true', help='if defined, more output is printed')
parser.add_argument('--buzzer', choices=['ON', 'OFF'], help='set buzzer ON/OFF')
parser.add_argument('--buzzer_volume', type=int, choices=range(0, 101), help='set buzzer volume')
parser.add_argument('--child_lock', choices=['ON', 'OFF'], help='set child lock ON/OFF')
parser.add_argument('--fan_level', type=int, choices=range(1, 4), help='set fan level')
parser.add_argument('--favorite_level', type=int, choices=range(0, 15), help='set favorite level')
parser.add_argument('--favorite_rpm', type=int, choices=range(300, 2301, 10), help='set favorite motor speed')
parser.add_argument('--led', choices=['ON', 'OFF'], help='turn led ON/OFF')
parser.add_argument('--led_brightness', choices=['Bright', 'Dim', 'Off'], help='set led brightness')
parser.add_argument('--mode', choices=['Auto', 'Silent', 'Favorite', 'Fan'], help='set mode')
parser.add_argument('--power', choices=['ON', 'OFF'], help='power ON/OFF')
parser.add_argument('IPaddress', help='IP address of the device')
parser.add_argument('token', help='token to login to the device')

args = parser.parse_args()

if args.debug:
    print(args)

MyAir = miio.airpurifier_miot.AirPurifierMiot(args.IPaddress, args.token)

if args.buzzer:
    MyAir.set_buzzer(args.buzzer == 'ON')

if args.buzzer_volume is not None:
    MyAir.set_volume(args.buzzer_volume)

if args.child_lock:
    MyAir.set_child_lock(args.child_lock == 'ON')

if args.fan_level:
    MyAir.set_fan_level(args.fan_level)

if args.favorite_level is not None:
    MyAir.set_favorite_level(args.favorite_level)

if args.favorite_rpm:
    MyAir.set_favorite_rpm(args.favorite_rpm)

if args.led:
    MyAir.set_led(args.led == 'ON')

if args.led_brightness:
    if args.led_brightness == "Bright":
            MyAir.set_led_brightness(miio.airpurifier_miot.LedBrightness.Bright)
    elif args.led_brightness == "Dim":
            MyAir.set_led_brightness(miio.airpurifier_miot.LedBrightness.Dim)
    elif args.led_brightness == "Off":
            MyAir.set_led_brightness(miio.airpurifier_miot.LedBrightness.Off)

if args.mode:
    if args.mode == "Auto":
            MyAir.set_mode(miio.airpurifier_miot.OperationMode.Auto)
    elif args.mode == "Silent":
            MyAir.set_mode(miio.airpurifier_miot.OperationMode.Silent)
    elif args.mode == "Favorite":
            MyAir.set_mode(miio.airpurifier_miot.OperationMode.Favorite)
    elif args.mode == "Fan":
            MyAir.set_mode(miio.airpurifier_miot.OperationMode.Fan)

if args.power:
    if args.power == "ON":
        MyAir.on()
    else:
        MyAir.off()

print(MyAir.status())

