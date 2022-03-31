#!/usr/bin/python
# -*- coding:utf-8 -*-
from pickle import FALSE
import sys
import os
import datetime
import json
import paho.mqtt.client as mqtt
import wand
from wand.display import display
import logging
from waveshare_epd import epd5in83b_V2
import time
from PIL import Image,ImageDraw,ImageFont
import urllib3

# epd
epd = epd5in83b_V2.EPD()

################################################################################
#### CHANGE THIS SECTION TO YOUR OWN SETTINGS ##################################
################################################################################
# configuration
mqttConString = '%your-mqtt-IP%'
mqttPort = 1883
mqttUsername = '%your-mqtt-username%'
mqttPassword = '%your-mqtt-password%'

# variables
solarOutput = '-'
solarYieldDay = '-'
solarCurrentOverflow = '-'
solarCurrentUsage = '-'
carPlugged = '-'
carCurrentLoad = '-'
newChangeAvailable = False
doFullRefresh = False
refreshInterval = 240
tempIndoor = '-'
tempOutdoor = '-'
tempM1 = '-'

# paths
picdir = './pic/'
fontdir = './font/'
libdir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'lib')
if os.path.exists(libdir):
    sys.path.append(libdir)

logging.basicConfig(level=logging.DEBUG)
http = urllib3.PoolManager()

################################################################################
#### Set your own font, they are not delivered in the repository ###############
################################################################################
logging.info("loading font")
fontFileName = 'UbuntuMono-Regular.ttf'

textSuperLarge = 56
textLarge = 38
textMedium = 28

fontSuperLarge = ImageFont.truetype(os.path.join(fontdir, fontFileName), textSuperLarge)
fontLarge = ImageFont.truetype(os.path.join(fontdir, fontFileName), textLarge)
fontMedium = ImageFont.truetype(os.path.join(fontdir, fontFileName), textMedium)
fontSmall = ImageFont.truetype(os.path.join(fontdir, fontFileName), 18)

################################################################################
#### ENABLE/DISABLE DEBUG MODE #################################################
################################################################################
Debug_Mode = os.getenv(PI_DEBUG, default = 0)

def on_connect(client, userdata, flags, rc):
    print("mqtt: connected with result code "+str(rc))
    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    client.subscribe("power/pv/#")
    client.subscribe("keba/garage")
    client.subscribe("netatmo/compact/#")

def internet_on():
    # connectigvity check, to an no SSL url
    try:
        r = http.request('GET', 'http://NeverSSL.com')
        if r.status == 200:
            return True
        else:
            return False
    except:
        return False

################################################################################
#### THIS PART DEPENDS ON YOUR LOCAL SETUP #####################################
################################################################################
# on every message received I try to extract the relevant data and update the
# the global variables with the new values
# My data is stored in a MQTT database on different topics, these topics are
# filled and updated over a NodeRed instance
def on_message(client, userdata, msg):
    global newChangeAvailable
    global solarOutput
    global solarYieldDay
    global solarCurrentOverflow
    global solarCurrentUsage
    global carPlugged
    global carCurrentLoad
    global tempIndoor
    global tempOutdoor
    global tempM1

    try:
        if msg.topic == 'power/pv/yieldDay':
            solarYieldDay = "{:.1f}".format(float(msg.payload) / 1000)
            newChangeAvailable = True

        if msg.topic == 'power/pv/output':
            solarOutput = "{:.1f}".format(float(msg.payload) / 1000)
            newChangeAvailable = True

        if msg.topic == 'power/pv/consumption':
            solarCurrentUsage = "{:.1f}".format(float(msg.payload) / 1000)
            solarCurrentOverflow = "{:.1f}".format(float(solarOutput) - float(solarCurrentUsage))
            newChangeAvailable = True

        if msg.topic == 'keba/garage':
            garageData = json.loads(msg.payload)
            if garageData["state"] == 'unplugged':
                carPlugged = 'off'
            else:
                carPlugged = 'on'
            carCurrentLoad = "{:.1f}".format(int(garageData["realPower"]))
            newChangeAvailable = True

        if msg.topic == 'netatmo/compact/indoor':
            temp = json.loads(msg.payload)
            tempIndoor = "{:.1f}".format(float(temp["temperature"]))
            newChangeAvailable = True

        if msg.topic == 'netatmo/compact/outdoor':
            temp = json.loads(msg.payload)
            tempOutdoor = "{:.1f}".format(float(temp["temperature"]))
            newChangeAvailable = True

        if msg.topic == 'netatmo/compact/m1':
            temp = json.loads(msg.payload)
            tempM1 = "{:.1f}".format(float(temp["temperature"]))
            newChangeAvailable = True
    except:
        logging.warning('mqtt error happened - try next time')

# main method, start gathering all information from MQTT and display it
def main():
    global newChangeAvailable

    logging.info("starting clock")

    logging.info("connect to mqtt")
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    client.username_pw_set(mqttUsername, mqttPassword)
    client.connect(mqttConString, mqttPort, 60)
    client.loop_start()

    # initial refresh, wait for some seconds for initial data
    if Debug_Mode == 0:
        time.sleep(5)
    else:
        time.sleep(10)

    refresh_paper()

    time.sleep(30)

    # periodical refresh
    while True:
        if (newChangeAvailable == True):
            newChangeAvailable = False
            refresh_paper()

        logging.info('waiting for %s' % refreshInterval)
        time.sleep(refreshInterval)

# helper method to align text correctly (left or right)
def add_align_text(paper, align, horizontal, top, content, font):
    if align == 'right':
        w, h = paper.textsize(content, font = font)
        paper.text((epd.width - w - horizontal, top), content, font = font, fill = 0)
    else:
        paper.text((horizontal, top), content, font = font, fill = 0)

# render method
def renderEnergyInfo(HBlackimage, black):
    # draw solar information
    solarTextTopDiff = 100
    solarIconTopDiff = solarTextTopDiff - 25
    energyLabelTopDiff = 25
    energyRightColumn = 260
    energyLegendRightColumn = energyRightColumn + 15
    energyLeftColumn = energyRightColumn + 160
    energyLegendLeftColumn = energyLeftColumn

    ################################################################################
    ###### Below I have commented out the icon part, because you have to get   #####
    ###### them for your own. I used licensed icons for my display.            #####
    ################################################################################

    # solarImage = Image.open(os.path.join(picdir, 'solar.jpg'))
    # HBlackimage.paste(solarImage, (10, solarIconTopDiff))
    add_align_text(paper = black, align = 'right', horizontal = energyRightColumn + 5, top = solarTextTopDiff, content = "%s kWh" % solarYieldDay, font = fontMedium)
    add_align_text(paper = black, align = 'right', horizontal = energyLegendRightColumn - 8, top = solarTextTopDiff + energyLabelTopDiff, content = "production", font = fontSmall)
    add_align_text(paper = black, align = 'right', horizontal = energyLeftColumn, top = solarTextTopDiff, content = "%s kW" % solarOutput, font = fontMedium)
    add_align_text(paper = black, align = 'right', horizontal = energyLegendLeftColumn, top = solarTextTopDiff + energyLabelTopDiff, content = "current", font = fontSmall)

    # draw solar 2 information
    solar2TextTopDiff = 220
    solar2IconTopDiff = solar2TextTopDiff - 25
    # solar2Image = Image.open(os.path.join(picdir, 'electric.jpg'))
    # HBlackimage.paste(solar2Image, (10, solar2IconTopDiff))
    add_align_text(paper = black, align = 'right', horizontal = energyRightColumn + 18, top = solar2TextTopDiff, content = "%s kW" % solarCurrentOverflow, font = fontMedium)
    add_align_text(paper = black, align = 'right', horizontal = energyLegendRightColumn + 2, top = solar2TextTopDiff + energyLabelTopDiff, content = "supply", font = fontSmall)
    add_align_text(paper = black, align = 'right', horizontal = energyLeftColumn, top = solar2TextTopDiff, content = "%s kW" % solarCurrentUsage, font = fontMedium)
    add_align_text(paper = black, align = 'right', horizontal = energyLegendLeftColumn, top = solar2TextTopDiff + energyLabelTopDiff, content = "consuption", font = fontSmall)

    # draw car information
    carTextTopDiff = 340
    carIconTopDiff = carTextTopDiff - 25
    carTextLeft = 130
    # carImage = Image.open(os.path.join(picdir, 'car.jpg'))
    # HBlackimage.paste(carImage, (10, carIconTopDiff))
    add_align_text(paper = black, align = 'right', horizontal = energyRightColumn + 18, top = carTextTopDiff, content = "%s kW" % carCurrentLoad, font = fontMedium)
    add_align_text(paper = black, align = 'right', horizontal = energyLegendRightColumn + 2, top = carTextTopDiff + energyLabelTopDiff, content = "loading", font = fontSmall)
    add_align_text(paper = black, align = 'right', horizontal = energyLeftColumn, top = carTextTopDiff, content = "%s" % carPlugged, font = fontMedium)
    add_align_text(paper = black, align = 'right', horizontal = energyLegendLeftColumn, top = carTextTopDiff + energyLabelTopDiff, content = "plugged", font = fontSmall)

def renderTemperature(black):
    # temperature / weather
    tempTopDiff = 100
    tempRightDiff = 100
    tempLegendRightDiff = 20
    add_align_text(paper = black, align = 'right', horizontal = tempRightDiff, top = tempTopDiff, content = "%s °C" % tempIndoor, font = fontMedium)
    add_align_text(paper = black, align = 'right', horizontal = tempLegendRightDiff, top = tempTopDiff + 10, content = "indoor", font = fontSmall)
    add_align_text(paper = black, align = 'right', horizontal = tempRightDiff, top = tempTopDiff + 50, content = "%s °C" % tempOutdoor, font = fontMedium)
    add_align_text(paper = black, align = 'right', horizontal = tempLegendRightDiff, top = tempTopDiff + 60, content = "outdoor", font = fontSmall)
    add_align_text(paper = black, align = 'right', horizontal = tempRightDiff, top = tempTopDiff + 100, content = "%s °C" % tempM1, font = fontMedium)
    add_align_text(paper = black, align = 'right', horizontal = tempLegendRightDiff, top = tempTopDiff + 110, content = "office", font = fontSmall)

def renderDateTime(black):
    now = datetime.datetime.now()

    # draw date and time
    rightBarShift = 425
    dateTextBottomDiff = textLarge + 30
    timeTextBottomDiff = dateTextBottomDiff + textSuperLarge + 20
    black.text((rightBarShift, epd.height - dateTextBottomDiff), "%s.%s.%s" % ('%02d' % now.day, '%02d' % now.month, now.year), font = fontLarge, fill = 0)


    # draw date and time
    dateTextBottomDiff = textLarge + 30
    timeTextBottomDiff = dateTextBottomDiff + textSuperLarge + 20
    black.text((rightBarShift, epd.height - timeTextBottomDiff), "%s : %s" % ('%02d' % now.hour, '%02d' % now.minute), font = fontSuperLarge, fill = 0)
    black.text((rightBarShift, epd.height - dateTextBottomDiff), "%s.%s.%s" % ('%02d' % now.day, '%02d' % now.month, now.year), font = fontLarge, fill = 0)

# refresh method
def refresh_paper():
    try:
        internetIsOn = False
        if Debug_Mode == 0:
            logging.info("init and clear")
            # epd.Clear()
            epd.init()
            internetIsOn = internet_on()
            # logging.info("*** reset call")
            # epd.reset()
        else:
            logging.info("DEBUG MODE")

        # drawing horizontal black image
        HBlackimage = Image.new('1', (epd.width, epd.height), 255)  # 648*480
        black = ImageDraw.Draw(HBlackimage)

        # drawing horizontal red image
        HRedimage = Image.new('1', (epd.width, epd.height), 255)  # 648*480  HRedimage: red
        red = ImageDraw.Draw(HRedimage)

        # drawing items
        black.line((400, 0, 400, 480), fill = 0)

        # network state
        # connectivity = Image.open(os.path.join(picdir, 'wlan.jpg'))
        connDiff = 35
        connHorizontalDiff = connDiff + 15
        # if internetIsOn:
        #     HBlackimage.paste(connectivity, (epd.width - connHorizontalDiff, connDiff))
        # else:
        #     HRedimage.paste(connectivity, (epd.width - connHorizontalDiff, connDiff))

        # renderEnergyInfo(HBlackimage, black)
        renderTemperature(black)
        renderDateTime(black)

        if Debug_Mode == 1:
            logging.info('debug mode enabled')
            HBlackimage.save('_debug_black.png')
            HRedimage.save('_debug_red.png')
            logging.info('writing debug files')
            wand.display.display(wand.image.Image(filename = '_debug_black.png'))
            wand.display.display(wand.image.Image(filename = '_debug_red.png'))
        else:
            epd.display(epd.getbuffer(HBlackimage), epd.getbuffer(HRedimage))
            time.sleep(2)
            logging.info("goto sleep...")
            epd.sleep()

    except IOError as e:
        logging.info(e)

    # shutdown application on a keyboard interrupt...
    except KeyboardInterrupt:
        logging.info("ctrl + c")
        epd.Clear()
        epd5in83b_V2.epdconfig.module_exit()
        exit()

    # ...or a system init command
    except SystemExit:
        logging.info("shutdown")
        epd.Clear()
        epd5in83b_V2.epdconfig.module_exit()
        exit()

if __name__ == '__main__':
    main()