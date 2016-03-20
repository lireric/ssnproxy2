#!/usr/bin/env python
from threading import Thread
from Queue import Queue
import paho.mqtt.client as mqtt
import serial
from ssn import ssnMsg
import string
#import threading
from datetime import datetime
import time
import json

# *******************************************
logQueue = Queue()

def logWrite(logMsg, level='w'):
    logQueue.put(str(datetime.now()) + " " + logMsg)
    return

def processTelemetry(teleData, ssnMsg):
     for teleItem in teleData['devs']:
         if (len(teleItem)):
              client.publish("/ssn/acc/"+str(ACCOUNT)+"/obj/"+
                  str(ssnMsg.srcObj)+"/device/"+str(teleItem['dev'])+"/"+str(teleItem['i'])+"/out",
                  payload=teleItem['val'], qos=0, retain=True)
              client.publish("/ssn/acc/"+str(ACCOUNT)+"/obj/"+
                  str(ssnMsg.srcObj)+"/device/"+str(teleItem['dev'])+"/"+str(teleItem['i'])+"/devicetime",
                  payload=teleItem['updtime'], qos=0, retain=True)

# The callback for when a PUBLISH message is received from the server from raw_data topic.
def sdv_callback(client, userdata, msg):
    #print(msg.topic+" "+str(msg.payload))
    logWrite("sdv: "+msg.topic+"->"+msg.payload, level="i")
    topicArray = string.rsplit(msg.topic,'/')
    dev = topicArray[len(topicArray)-3]
    ch = topicArray[len(topicArray)-2]
    obj = topicArray[len(topicArray)-5]
    # make set dev value command:
    sdv = '{"ssn":{"v":1,"obj":'+obj+',"cmd":"sdv", "data": {"adev":'+dev+',"acmd":'+ch+',"aval":'+msg.payload+'}}}"'
#    logWrite("sdv= "+sdv, level="i")
    tmpMsg = ssnMsg(destObj=int(obj),  srcObj=0, msgType=2, msgID=None, msgData=sdv)
    client.publish("/ssn/acc/" + str(ACCOUNT)+"/obj/" + obj+"/commands",
                  tmpMsg.getSSNPDU(), qos=0, retain=False)

# The callback for when a PUBLISH message is received from the server from raw_data topic.
def raw_data_callback(client, userdata, msg):
    #print(msg.topic+" "+str(msg.payload))
    logWrite("raw_data: "+msg.topic+"->", level="i")
    logWrite(msg.payload, level="d")
    tail = msg.payload
    while len(tail):
        tmpMsg = ssnMsg()
        tail, nResult = tmpMsg.processBuffer(tail)
        if (nResult):
            if (tmpMsg.msgType == 6):
                #process LOG message
#            if (tmpMsg.destObj in serial_if):
                logWrite("LOG message, src Obj="+str(tmpMsg.srcObj), level="i")
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
                    logWrite("Cannot decode JSON object, payload={}: {}".format(tmpMsg.msgData,ex), level="e")
            elif (tmpMsg.msgType == 2):
                #process JSON message
                logWrite("JSON message, src Obj="+str(tmpMsg.srcObj), level="i")
            elif (tmpMsg.msgType == 3):
                #process TELEMETRY message
                logWrite("TELEMETRY message, src Obj="+str(tmpMsg.srcObj), level="i")
                try:
                    ssn_data = json.loads(tmpMsg.msgData)
                    if (ssn_data['ssn']['ret'] == "getdevvals"):
                        processTelemetry(ssn_data['ssn']['data'], tmpMsg)
                except Exception as ex:
                    logWrite("Cannot decode JSON object, payload={}: {}".format(tmpMsg.msgData,ex), level="e")
            else:
                logWrite("skip row data processing", level="i")
                
# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    logWrite("Connected with result code "+str(rc))

    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    client.subscribe([("/ssn/acc/"+str(ACCOUNT)+"/raw_data", 0), ("/ssn/acc/"+str(ACCOUNT)+"/obj/+/commands", 0),
                      ("/ssn/acc/"+str(ACCOUNT)+"/obj/+/device/+/+/in", 0)])


# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    #print(msg.topic+" "+str(msg.payload))
    logWrite(msg.topic+"->"+msg.payload)
    tail = msg.payload
    while len(tail):
        tmpMsg = ssnMsg()
        tail, nResult = tmpMsg.processBuffer(tail)
        # send message into serial interface if obj_dest in serials route list
        if (nResult):
            if (tmpMsg.destObj in serial_if):
                logWrite("route into serial, dest Obj="+str(tmpMsg.destObj), level="i")
                # use serial interface
                ser1.setRTS(True)
            #        time.sleep(0.5)
                ser1.write(str(msg.payload))
                while (ser1.outWaiting() > 0):
                    time.sleep(0.01)
                ser1.setRTS(False)
            else:
                logWrite("skip serial routing", level="i")


def logQProc():
    while True:
        item = logQueue.get()
        print item
        logQueue.task_done()

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
    logWrite( "Serial listener started. Dev: "+ser.port)
    tail = ""
    while(1):
#        print "read.."
        ser.setRTS(False)
        buf = tail + ser.read(SerialBufferSize)
        if (buf):
            ledon()
            logWrite("BUF:"+buf)
#            logWrite("TAIL:"+tail)
            #tail = processBuffer(buf, channel=0, ser=ser)
#            client.publish(TOPIC_PROC_DATA, payload=buf, qos=0, retain=False)
            try:
                client.publish("/ssn/acc/"+str(ACCOUNT)+"/raw_data", payload=buf, qos=0, retain=False)
            except Exception, e:
                logWrite("Error publishing message"+str(e), "e")
            ledoff()
#            for i in buf:
#                value = struct.unpack('B', i)[0]
#                print "%02x" % (value),
    logWrite( "Exit serial")
    return


# ---------------------------------------------- globals:
config = {}
execfile("ssnmqtt.cfg", config) 
# objects routing interfaces
serial_if = config["serial_if"]
#tcp_if = config["tcp_if"]
Serialbaudrate=config["Serialbaudrate"]
SerialPort=config["SerialPort"]
SerialBufferSize=config["SerialBufferSize"]
Serialrtscts=config["Serialrtscts"]

ssnTimeout = config["SSNTimeout"]
SerialTimeout = config["SerialTimeout"]

TCPBufferSize=config["TCPBufferSize"]
MQTT_HOST = config["MQTT_HOST"]             # mqtt boker host
MQTT_PORT = config["MQTT_PORT"]             # mqtt boker port 
MQTT_BROKER_USER = config["MQTT_BROKER_USER"]     # mqtt broker user
MQTT_BROKER_PASS = config["MQTT_BROKER_PASS"]     # mqtt broker password
MQTT_BROKER_CLIENT_ID = config["MQTT_BROKER_CLIENT_ID"] # broker client id
LED_BLINK = config["LED_BLINK"]

ACCOUNT = config["ACCOUNT"]
#TOPIC_COMMANDS = config["TOPIC_COMMANDS"]
#TOPIC_PROC_DATA = config["TOPIC_PROC_DATA"]

ser1 = serial.Serial(
    port=SerialPort,
    baudrate=Serialbaudrate,
    timeout=SerialTimeout,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    rtscts = Serialrtscts,
    bytesize=serial.EIGHTBITS
)


# ============================================================================
if __name__ == "__main__":
    ser1.setRTS(False)
    queue = Queue()
#    logWrite (strTest)
#    testTail = processBuffer(strTest)
    workerLog = Thread(target=logQProc)
    workerLog.setDaemon(True)
    workerLog.start()
    print "Start serial listener"
    workerSerial = Thread(target=listenerSerial, args=(ser1, queue))
    workerSerial.setDaemon(True)
    workerSerial.start()
    
    client = mqtt.Client(client_id=MQTT_BROKER_CLIENT_ID)
    client.on_connect = on_connect
    client.on_message = on_message
    client.raw_data_callback = raw_data_callback
    client.message_callback_add("/ssn/acc/"+str(ACCOUNT)+"/raw_data", raw_data_callback)
    client.sdv_callback = sdv_callback
    client.message_callback_add("/ssn/acc/"+str(ACCOUNT)+"/obj/+/device/+/+/in", sdv_callback)

    client.username_pw_set(MQTT_BROKER_USER, password=MQTT_BROKER_PASS)
    
    client.connect(MQTT_HOST, MQTT_PORT, 60)
    
    # Blocking call that processes network traffic, dispatches callbacks and
    # handles reconnecting.
    # Other loop*() functions are available that give a threaded interface and a
    # manual interface.
    client.loop_forever()
