"""Creted on: 13.04.2018
   Author: Dario Mader
   Supporter: Lukas Leuthold
   Brief: Attachs to Swisscom LTE CAT M1 network and sends Bosch BME280 sensor data to mqtt broker over tls
   Version: 1.0
   License: Free - do what you want (provided you leave the credits)
"""


import socket
import ssl
import time
import pycom
from network import LTE
from mqtt import MQTTClient
from machine import I2C
import bme280
import json
import utime
import re


def send_at_cmd_pretty(cmd):
    response = lte.send_at_cmd(cmd).split('\r\n')
    for line in response:
        print(line)

lte = LTE()
send_at_cmd_pretty('AT+CPIN?')
send_at_cmd_pretty('AT+CGDCONT=1,"IP","swisscom-test.m2m.ch"')
send_at_cmd_pretty('AT+CFUN=0')
send_at_cmd_pretty('AT+CEREG=2')
send_at_cmd_pretty('AT!="clearscanconfig"')
send_at_cmd_pretty('AT!="RRC::addscanfreq band=20 dl-earfcn=6300"')
send_at_cmd_pretty('AT+CFUN=1')


pycom.heartbeat(False)

while not lte.isattached():
    pycom.rgbled(0x7f0000)
    time.sleep(0.1)
    pycom.rgbled(0x000000)
    time.sleep(0.5)
    send_at_cmd_pretty('AT!="showphy"')
    send_at_cmd_pretty('AT!="fsm"')
    send_at_cmd_pretty('AT+CEREG?')


lte.connect()
while not lte.isconnected():
    pycom.rgbled(0x7f7f00)
    time.sleep(0.1)
    pycom.rgbled(0x000000)
    time.sleep(0.5)
    print("waiting")

client = MQTTClient("client", "domain",user="user", password="password", port=port, ssl = True)

i2c = I2C(0, I2C.MASTER, baudrate=100000, pins=('G9', 'G10'))
scanner = i2c.scan()
print(scanner)
bme = bme280.BME280(i2c=i2c)

#pycom.heartbeat(True)
while lte.isconnected():
    pycom.rgbled(0x007f00)
    part = ".*?(-*\d+\.*\d*).*?"
    try:
        cellinfo = lte.send_at_cmd('AT+VZWRSRP')
        m = re.search('.*?:{},{},{}'.format(part,part,part), cellinfo)
        pci = int(m.group(1))
        earfcn = int(m.group(2))
        rsrp = float(m.group(3))
        print("RSRP: " + str(rsrp))
        print("PCI:" + str(pci))
        print("EARFCN: " + str(earfcn))
    except:
        pass
        pci = 0
        earfcn = 0
        rsrp = 0
    print("Getting sensor vlaues...")
    airpressure = bme.pressure[:-3]
    time.sleep(2)
    airpressure = float(airpressure)
    airpressure = (airpressure / pow(1.0 - 526/44330.0, 5.255))
    temperature = float(bme.temperature[:-1])
    humidity = float(bme.humidity[:-1])
    sensordata = {"temperature":temperature,"airpressure":airpressure,"humidity":humidity,"pci":pci,"earfcn":earfcn,"rsrp":rsrp}
    json_data = json.dumps(sensordata)
    print("Connecting to MQTT Broker at damn.li....")
    try:
        client.connect()
        print("Publishing sensor values....")
        client.publish(topic="topic", msg=json_data)
        pycom.rgbled(0x000000)
        time.sleep(0.2)
        pycom.rgbled(0x007f00)
        time.sleep(0.2)
        pycom.rgbled(0x000000)
        time.sleep(0.2)
        pycom.rgbled(0x007f00)
        print("Disconnecting....")
        client.disconnect()
    except:
        pass
    print("Waiting for next publishing phase... Happy IoT!")
    time.sleep(30)
pycom.heartbeat(True)
