#!/usr/bin/env python
import logging
import logging.handlers
import serial
import string
import time
import json
import random
#from builtins import str
HAVE_TLS = True
try:
    import ssl
except ImportError:
    HAVE_TLS = False

from datetime import datetime
from threading import Thread
from Queue import Queue

import paho.mqtt.client as mqtt

# --- SSN custom modules:
from ssn import ssnMsg
from ssntelegram import ssnTlg

# *******************************************
#logQueue = Queue()
sendQueue = Queue()
serLastReceive = 0
global client
client = ""
global g_tail
g_tail = ""

#def logWrite(logMsg, level='w'):
#    logQueue.put(str(datetime.now()) + " " + logMsg)
#    return

def getProxyObj():
    global proxy_obj
    return proxy_obj

def getTlgIf():
    global tlg_if
    return tlg_if
    
def getTlgDev():
    global tlg_dev
    return tlg_dev

def serPutMsg(buf):
#    logWrite("serPutMsg")
    sendQueue.put(buf)
    return

def serRead(ser, bufSize):
    ser.setRTS(False)
    if (len(RTS_GPIO)):
        value = open("/sys/class/gpio/gpio"+str(RTS_GPIO)+"/value","w")
        value.write(RTS_PASSIVE)
        value.close()
    return ser.read(bufSize)

def serWrite(ser, buf):
#    logWrite( "serWrite")
    ser.setRTS(True)
    if (len(RTS_GPIO)):
        value = open("/sys/class/gpio/gpio"+str(RTS_GPIO)+"/value","w", 0)
        value.write(RTS_ACTIVE)
        value.flush()
#        time.sleep(0.0005)
    ser.write(buf)
#    while (ser.outWaiting() > 0):
    while (ser.out_waiting > 0):
        time.sleep(0.001)
    ser.flush()
    ser.setRTS(False)
    if (len(RTS_GPIO)):
        time.sleep(0.005)
        value.write(RTS_PASSIVE)
        value.flush()
        value.close()

def processTelemetry(teleData, ssnMsg):
    tlgBuf = ""
    for teleItem in teleData['devs']:
        if (len(teleItem)):
            client.publish("/ssn/acc/"+str(ACCOUNT)+"/obj/"+
                  str(ssnMsg.srcObj)+"/device/"+str(teleItem['dev'])+"/"+str(teleItem['i'])+"/out",
                  payload=teleItem['val'], qos=0, retain=True)
                      
            client.publish("/ssn/acc/"+str(ACCOUNT)+"/obj/"+
                  str(ssnMsg.srcObj)+"/device/"+str(teleItem['dev'])+"/"+str(teleItem['i'])+"/devicetime",
                  payload=teleItem['updtime'], qos=0, retain=True)
                  
            if (ssnMsg.destObj == getTlgIf()):
                strBuf = "d["+str(teleItem['dev'])+","+str(teleItem['i'])+"]="+str(teleItem['val'])
                tlgBuf += strBuf+"\r\n"
                
    # check for Telegram dest:
    if (ssnMsg.destObj == getTlgIf()):
                logger1.debug("route to Telegram: "+strBuf, level="i")
                client.publish("/ssn/acc/"+str(ACCOUNT)+"/telegram/out",
                  payload=tlgBuf, qos=0, retain=False)


def send_command(strCmd, nCmdType, destObj):
    ssnTempMsg = ssnMsg(destObj=destObj,  srcObj=getProxyObj(), msgType=nCmdType, msgID=None, \
    msgData=strCmd, msgChannel=None, msgSocket=None, msgSerial=None)

    client.publish("/ssn/acc/" + str(ACCOUNT)+"/obj/" + str(destObj)+"/commands",
                  ssnTempMsg.getSSNPDU(), qos=0, retain=False)
    
def cmd_ini_callback(client, userdata, msg):
    topicArray = string.rsplit(msg.topic,'/')
    obj = topicArray[len(topicArray)-3]
    logger1.debug("Command INI-type: "+msg.topic+"->"+msg.payload, level="i")

    send_command(strCmd = msg.payload, nCmdType = 7, destObj = int(obj))

def cmd_json_callback(client, userdata, msg):
    topicArray = string.rsplit(msg.topic,'/')
    obj = topicArray[len(topicArray)-3]

    logger1.debug("Command JSON-type: "+msg.topic+"->"+msg.payload, level="i")
    send_command(strCmd = msg.payload, nCmdType = 2, destObj = int(obj))


# --- messages to Telegram bot:
def tlg_data_callback(client, userdata, msg):
    global ssnbot
    logger1.debug("Telegram out: "+msg.topic+"->"+msg.payload, level="i")
    if (ssnbot):
        ssnbot.sendTlgMessage(msg.payload)
    
def tlg_photo_callback(client, userdata, msg):
    global ssnbot
    logger1.debug("Telegram out/photo: "+msg.topic, level="i")
    if (ssnbot):
        ssnbot.sendTlgPhoto(msg.payload)
    
# The callback for when a PUBLISH message is received from the server from raw_data topic.
def sdv_callback(client, userdata, msg):
    #print(msg.topic+" "+str(msg.payload))
    logger1.debug("sdv: "+msg.topic+"->"+msg.payload, level="i")
    topicArray = string.rsplit(msg.topic,'/')
    dev = topicArray[len(topicArray)-3]
    ch = topicArray[len(topicArray)-2]
    obj = topicArray[len(topicArray)-5]
    if (int(dev) == getTlgDev()):
        logger1.debug("route to Telegram device: "+msg.payload, level="i")
        client.publish("/ssn/acc/"+str(ACCOUNT)+"/telegram/out",
        payload=msg.payload, qos=0, retain=False)
    else:
        # make set dev value command:
        sdv = '{"ssn":{"v":1,"obj":'+obj+',"cmd":"sdv", "data": {"adev":'+dev+',"acmd":'+ch+',"aval":'+msg.payload+'}}}"'
#    logWrite("sdv= "+sdv, level="i")
        tmpMsg = ssnMsg(destObj=int(obj),  srcObj=0, msgType=2, msgID=None, msgData=sdv)
        client.publish("/ssn/acc/" + str(ACCOUNT)+"/obj/" + obj+"/commands",
                  tmpMsg.getSSNPDU(), qos=0, retain=False)

# The callback for when a PUBLISH message is received from the server from raw_data topic.
def raw_data_callback(client, userdata, msg):
    global g_tail
    #print(msg.topic+" "+str(msg.payload))
    msg_len = len(msg.payload)
    logger1.debug("raw_data: "+msg.topic+"->")
    logger1.debug(msg.payload)
#    g_tail = g_tail + msg.payload
    g_tail = msg.payload # TO DO..
    tail = ""

    while (len(tail) < msg_len):
        msg_len = len(tail)
        tmpMsg = ssnMsg()
        tail, nResult = tmpMsg.processBuffer(g_tail)
        if (nResult):
            logger1.info("LOG raw_data message: srcObj="+str(tmpMsg.srcObj)+", destObj="+str(tmpMsg.destObj))

            if (len(g_tail) > 10000):  # check buffer owerflow
                logger1.warn("SSN packet buffer overflow!")
                g_tail = ""
            else:
                g_tail = tail

            if (tmpMsg.msgType == 6):
                #process LOG message
#            if (tmpMsg.destObj in serial_if):
                logger1.debug("LOG message, src Obj="+str(tmpMsg.srcObj))
                try:
                    ssn_data = json.loads(tmpMsg.msgData)
                    for logItem in ssn_data['log']:
                        # publish event into events topic and devices values into its topics:
                        if (len(logItem)):
                            client.publish("/ssn/acc/"+str(ACCOUNT)+"/obj/"+str(tmpMsg.srcObj)+"/events",
                                           payload=json.dumps(logItem), qos=0, retain=False)
                            client.publish("/ssn/acc/"+str(ACCOUNT)+"/obj/"+
                                str(tmpMsg.srcObj)+"/device/"+str(logItem['d'])+"/"+str(logItem['c'])+"/out",
                                payload=logItem['v'], qos=0, retain=True)
                            client.publish("/ssn/acc/"+str(ACCOUNT)+"/obj/"+
                                str(tmpMsg.srcObj)+"/device/"+str(logItem['d'])+"/"+str(logItem['c'])+"/devicetime",
                                payload=logItem['t'], qos=0, retain=True)
                except Exception as ex:
                    logger1.error("Cannot decode JSON object, payload={}: {}".format(tmpMsg.msgData,ex))
            elif (tmpMsg.msgType == 2):
                #process JSON message
                logger1.info("JSON message, src Obj="+str(tmpMsg.srcObj))
            elif (tmpMsg.msgType == 3):
                #process TELEMETRY message
                logger1.debug("TELEMETRY message, src_Obj="+str(tmpMsg.srcObj)+" dst_Obj="+str(tmpMsg.destObj))
                try:
#                    logWrite("JSON: "+tmpMsg.msgData, level="d")
                    ssn_data = json.loads(tmpMsg.msgData)
                except Exception as ex:
                    logger1.error("TELEMETRY. Cannot decode JSON object, payload={}: {}".format(tmpMsg.msgData,ex))
                if (ssn_data['ssn']['ret'] == "getdevvals"):
                    processTelemetry(ssn_data['ssn']['data'], tmpMsg)
            else:
                logger1.debug("skip row data processing")
                
# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    logger1.info("Connected with result code "+str(rc))

    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    client.subscribe([("/ssn/acc/"+str(ACCOUNT)+"/raw_data", 0), 
                      ("/ssn/acc/"+str(ACCOUNT)+"/obj/+/commands", 0),
                      ("/ssn/acc/"+str(ACCOUNT)+"/obj/+/commands/ini", 0),
                      ("/ssn/acc/"+str(ACCOUNT)+"/obj/+/commands/json", 0),
                      ("/ssn/acc/"+str(ACCOUNT)+"/telegram/out", 0),
                      ("/ssn/acc/"+str(ACCOUNT)+"/telegram/out/photo", 0),
                      ("/ssn/acc/"+str(ACCOUNT)+"/obj/+/device/+/+/in", 0)])


# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    #print(msg.topic+" "+str(msg.payload))
    global g_tail
    msg_len = len(msg.payload)
    logger1.debug(msg.topic+" -> "+msg.payload)
#    tail = msg.payload
#    g_tail = g_tail + msg.payload
    g_tail = msg.payload
    tail = ""

    while (len(tail) < msg_len):
        msg_len = len(tail)
#    while len(tail):
        tmpMsg = ssnMsg()
        tail, nResult = tmpMsg.processBuffer(g_tail)
        # send message into serial interface if obj_dest in serials route list
        if (nResult):
            logger1.info("LOG routing message: srcObj="+str(tmpMsg.srcObj)+", destObj="+str(tmpMsg.destObj))
            if (len(g_tail) > 10000):  # check buffer owerflow
                logger1.warn("Buffer overflow!")
                g_tail = ""
            else:
                g_tail = tail

            if (tmpMsg.destObj in serial_if):
                logger1.info("route into serial, destObj="+str(tmpMsg.destObj)+", srcObj="+str(tmpMsg.srcObj))
                # use serial interface
#                serWrite(ser1, str(msg.payload))
                serPutMsg(str(msg.payload))
#                ser1.setRTS(True)
#                ser1.write(str(msg.payload))
#                while (ser1.outWaiting() > 0):
#                    time.sleep(0.01)
#                ser1.setRTS(False)
            elif (tmpMsg.destObj == tlg_if):
                logger1.info("route to Telegram: "+msg.topic+"->"+msg.payload)
                if (ssnbot):
                    ssnbot.sendTlgMessage(msg.payload)
            else:
                logger1.info("skip serial routing")


def serQProc():
    global serLastReceive
    while True:
        buf = sendQueue.get()
        tDelta = datetime.now() - serLastReceive
        # wait random time if last reading operation < SSNsendMinTimeout
        if (tDelta.total_seconds() < SSNsendMinTimeout):
            time.sleep(SSNsendMinTimeout + SSNsendMinTimeout * random.random())
        logger1.debug("LastReceive delta: "+str(tDelta))
        logger1.info("sending to serial")
        serWrite(ser1, buf)

#def logQProc():
#    global client
#    while True:
#        item = logQueue.get()
#        print item
#        if (LOG_TO_MQTT and client):
#            try:
#                client.publish("/ssn/acc/" + str(ACCOUNT)+"/log/ssnmqtt",
#                      item, qos=0, retain=False)
#            except Exception, e:
#                logWrite("Error publishing log message"+str(e), "e")
#        logQueue.task_done()

def ledon():
    if (len(LED_BLINK)):
        value = open("/sys/class/leds/"+LED_BLINK+"/brightness","w")
        value.write(str(1))
        value.close()

def ledoff():
    if (len(LED_BLINK)):
        value = open("/sys/class/leds/"+LED_BLINK+"/brightness","w")
        value.write(str(0))
        value.close()


        
def listenerSerial(ser, queue):
    logger1.info("Serial listener started. Dev: "+ser.port)
    global serLastReceive
    tail = ""
    while(1):
#        print "read.."
#        ser.setRTS(False)
#        buf = tail + ser.read(SerialBufferSize)
        try:
#            buf = tail + serRead(ser, SerialBufferSize)
            buf = serRead(ser, SerialBufferSize).decode('utf-8','ignore').encode("utf-8")
            serLastReceive = datetime.now()
            if (buf):
                ledon()
#               logWrite("Serial buf[01]{:02X}{:02X}".format(ord(buf[0]),ord(buf[1])), level="d")
                logger1.debug("BUF:"+buf[0:50]+"...")
#               logWrite("TAIL:"+tail)
                #tail = processBuffer(buf, channel=0, ser=ser)
#               client.publish(TOPIC_PROC_DATA, payload=buf, qos=0, retain=False)
                try:
                    client.publish("/ssn/acc/"+str(ACCOUNT)+"/raw_data", payload=buf, qos=0, retain=False)
                except Exception as e:
                    logger1.error("Error publishing message"+unicode(e))
                ledoff()
#               for i in buf:
#                    value = struct.unpack('B', i)[0]
#                   print "%02x" % (value),
        except Exception as ex:
                logger1.error("Error in receiving from serial:"+unicode(ex))
    logger1.info("Exit serial")
    return


# ---------------------------------------------- globals:
config = {}
execfile("ssnmqtt.cfg", config) 
# objects routing interfaces
proxy_obj = config["proxy_obj"]
serial_if = config["serial_if"]
#tcp_if = config["tcp_if"]
tlg_if = int(config["tlg_if"])

# Telegram virtual device
try:
    tlg_dev = int(config["tlg_dev"])
except:
    tlg_dev = ""

Serialbaudrate=config["Serialbaudrate"]
SerialPort=config["SerialPort"]
SerialBufferSize=config["SerialBufferSize"]
Serialrtscts=config["Serialrtscts"]

ssnTimeout = config["SSNTimeout"]
SerialTimeout = config["SerialTimeout"]
SSNsendMinTimeout = config["SSNsendMinTimeout"]

TCPBufferSize=config["TCPBufferSize"]
MQTT_HOST = config["MQTT_HOST"]             # mqtt boker host
MQTT_PORT = config["MQTT_PORT"]             # mqtt boker port 
MQTT_BROKER_USE_TLS = config["MQTT_BROKER_USE_TLS"] # 1: use TLS, 0: use login/password

try:
    MQTT_BROKER_USER = config["MQTT_BROKER_USER"]     # mqtt broker user
    MQTT_BROKER_PASS = config["MQTT_BROKER_PASS"]     # mqtt broker password
    MQTT_BROKER_CLIENT_ID = config["MQTT_BROKER_CLIENT_ID"] # broker client id
except:
    MQTT_BROKER_USER = ""
    MQTT_BROKER_PASS = ""
    MQTT_BROKER_CLIENT_ID = ""
try:
    MQTT_BROKER_CA_CERTS = config["MQTT_BROKER_CA_CERTS"] # path to CA dir
    MQTT_BROKER_CERTFILE = config["MQTT_BROKER_CERTFILE"] # strings pointing to the PEM encoded client certificate
    MQTT_BROKER_KEYFILE = config["MQTT_BROKER_KEYFILE"]   # strings pointing to the PEM encoded private key
except:
    MQTT_BROKER_CA_CERTS = ""
    MQTT_BROKER_CERTFILE = ""
    MQTT_BROKER_KEYFILE = ""

LED_BLINK = config["LED_BLINK"]
RTS_GPIO = config["RTS_GPIO"]
RTS_ACTIVE = config["RTS_ACTIVE"]
RTS_PASSIVE = config["RTS_PASSIVE"]

ACCOUNT = config["ACCOUNT"]

# --- Telegram bot settings:
try:
    TEL_TOKEN = config["TEL_TOKEN"]
    SSN_GRP_ID = config["SSN_GRP_ID"]
except:
    TEL_TOKEN = ""

try:
    LOG_TO_MQTT = config["LOG_TO_MQTT"]
except:
    LOG_TO_MQTT = ""
    
ser1 = serial.Serial(
    port=SerialPort,
    baudrate=Serialbaudrate,
    timeout=SerialTimeout,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
#    rtscts = False,
    rtscts = Serialrtscts,
    bytesize=serial.EIGHTBITS
)


# ============================================================================
if __name__ == "__main__":
    logger1 = logging.getLogger('ssnmqtt')
    logger1.setLevel(logging.DEBUG)
    # create syslog handler
    slh = logging.handlers.SysLogHandler(address = '/dev/log')
    # create console handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)

    formatter = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')
    slh.setFormatter(formatter)
    slh.setLevel(logging.INFO)
    ch.setFormatter(formatter)
    logger1.addHandler(slh)
    logger1.addHandler(ch)

    import sys  

    reload(sys)  
    sys.setdefaultencoding('utf8')

    if (len(RTS_GPIO)):
        value = open("/sys/class/gpio/export","w")
        value.write(RTS_GPIO)
        time.sleep(0.5)
        try:
            value.flush()
            value = open("/sys/class/gpio/gpio"+str(RTS_GPIO)+"/direction","w")
            value.write("out")
        except:
            time.sleep(1.5)
            value = open("/sys/class/gpio/gpio"+str(RTS_GPIO)+"/direction","w")
            value.write("out")
        value.close()

    ser1.setRTS(False)
    queue = Queue()
#    workerLog = Thread(target=logQProc)
#    workerLog.setDaemon(True)
#    workerLog.start()
    
    client = mqtt.Client(client_id=MQTT_BROKER_CLIENT_ID)
    client.on_connect = on_connect
    client.on_message = on_message

    client.raw_data_callback = raw_data_callback
    client.message_callback_add("/ssn/acc/"+str(ACCOUNT)+"/raw_data", raw_data_callback)

    client.cmd_ini_callback = cmd_ini_callback
    client.message_callback_add("/ssn/acc/"+str(ACCOUNT)+"/obj/+/commands/ini", cmd_ini_callback)

    client.cmd_json_callback = cmd_json_callback
    client.message_callback_add("/ssn/acc/"+str(ACCOUNT)+"/obj/+/commands/json", cmd_json_callback)

    client.sdv_callback = sdv_callback
    client.message_callback_add("/ssn/acc/"+str(ACCOUNT)+"/obj/+/device/+/+/in", sdv_callback)

    client.tlg_data_callback = tlg_data_callback
    client.message_callback_add("/ssn/acc/"+str(ACCOUNT)+"/telegram/out", tlg_data_callback)

    client.tlg_photo_callback = tlg_photo_callback
    client.message_callback_add("/ssn/acc/"+str(ACCOUNT)+"/telegram/out/photo", tlg_photo_callback)

    if (MQTT_BROKER_USER):
        client.username_pw_set(MQTT_BROKER_USER, password=MQTT_BROKER_PASS)

    if (HAVE_TLS and MQTT_BROKER_USE_TLS == 1):
# -- use TLS    
        logger1.info("Use TLS")
        client.tls_set(MQTT_BROKER_CA_CERTS, certfile=MQTT_BROKER_CERTFILE, keyfile=MQTT_BROKER_KEYFILE, cert_reqs=ssl.CERT_REQUIRED,
            tls_version=ssl.PROTOCOL_TLSv1, ciphers=None)
        client.tls_insecure_set(True)
    else:
# -- use login/passw    
        logger1.info("Use login/passw")

    
#    try:
#        client.connect(MQTT_HOST, MQTT_PORT, 60)
#    except Exception, e:
#        print("Cannot connect to MQTT broker at %s:%d: %s" % (MQTT_HOST, MQTT_PORT, str(e)))
#        sys.exit(2)

    logger1.info("Start send queue listener")
    workerSendQ = Thread(target=serQProc)
    workerSendQ.setDaemon(True)
    workerSendQ.start()
    logger1.info("Start serial listener")
    workerSerial = Thread(target=listenerSerial, args=(ser1, queue))
    workerSerial.setDaemon(True)
    workerSerial.start()
    
# --- start Telegram bot:
    if (TEL_TOKEN):
        logger1.info("Starting Telegram bot")
        logger1.info("Telegram obj="+str(getTlgIf())+", Telegram virtual device = "+str(getTlgDev()))
        ssnbot = ssnTlg(TEL_TOKEN, SSN_GRP_ID, acc = ACCOUNT, client = client, tlg_obj = getTlgIf())
    
    # Blocking call that processes network traffic, dispatches callbacks and
    # handles reconnecting.
    # Other loop*() functions are available that give a threaded interface and a
    # manual interface.
    while True:
        try:
            client.connect(MQTT_HOST, MQTT_PORT, 60)
            client.loop_forever()
#        except socket.error:
#            print("Cannot connect to MQTT broker at %s:%d: %s" % (MQTT_HOST, MQTT_PORT, str(e)))
#            print("socket.error. MQTT server disconnected; sleeping")
#            time.sleep(5)
        except Exception, e:
            # FIXME: add logging with trace
            print("MQTT exception"+str(e))
            time.sleep(5)
#            raise
