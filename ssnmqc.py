#!/usr/bin/env python
from ssn import ssnMsg
#from ssnmqtt import config, SSNTimeout
import sys, getopt
import paho.mqtt.client as mqtt
import time

# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    print >> sys.stderr, "Connected with result code "+str(rc)

# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    print(msg.topic+" "+msg.payload)

def on_publish(client, userdata, mid):
    print("\npublished: "+str(mid))

def main(argv):
    inputfile = ''
    destObj = 0
    srcObj = 3
    msgType = 2
    msgID = None
    msgData = ""
    
    try:
       opts, args = getopt.getopt(argv,"hd:fstiD",["file=","dest=","src=","type=","id=","data="])
    except getopt.GetoptError:
       print 'ssnmqc.py [--file <inputfile> or -D <data string>] --dest <destObj> -src <srcObj> --type <msgType> --id <msgID>'
       sys.exit(2)
    for opt, arg in opts:
       if opt == '-h':
           print 'ssnmqc.py [--file <inputfile> or -D <data string>] --dest <destObj> -src <srcObj> --type <msgType> --id <msgID>'
           sys.exit()
       if opt in ("-f", "--file"):
          inputfile = arg
       if opt in ("-d", "--dest"):
         destObj = int(arg, 10)
       if opt in ("-s", "--src"):
         srcObj = int(arg, 10)
       if opt in ("-t", "--type"):
         msgType = int(arg, 10)
       if opt in ("-i", "--id"):
         msgID = arg
       if opt in ("-D", "--data"):
         msgData = arg
    if (inputfile):
        with open(inputfile) as f:
            msgData = f.read()

#    print "QQQ: " + destObj
#    data = '{"ssn":{"v":1,"obj":10,"cmd":"getdevvals", "data": {"g":1}}}'
    config = {}
    execfile("ssnmqtt.cfg", config) 
#    TCPBufferSize = config["TCPBufferSize"]
    MQTT_HOST = config["MQTT_HOST"]             # mqtt boker host
    MQTT_PORT = config["MQTT_PORT"]             # mqtt boker port 
    MQTT_BROKER_USER = config["MQTT_BROKER_USER"]     # mqtt broker user
    MQTT_BROKER_PASS = config["MQTT_BROKER_PASS"]     # mqtt broker password
    MQTT_BROKER_CLIENT_ID = config["MQTT_BROKER_CLIENT_ID"] # broker client id
    ssnTimeout = config["SSNTimeout"]

#    TOPIC_COMMANDS = config["TOPIC_COMMANDS"]
    ACCOUNT = config["ACCOUNT"]

    client = mqtt.Client(client_id=MQTT_BROKER_CLIENT_ID)
    client.on_connect = on_connect
    client.on_message = on_message
    client.on_publish = on_publish
    client.username_pw_set(MQTT_BROKER_USER, password=MQTT_BROKER_PASS)
    client.connect(MQTT_HOST, MQTT_PORT, 60)

    nTimeIncrement = 0.01
    nTimeout = ssnTimeout
    nRes = 1
    while ((client._state != mqtt.mqtt_cs_connected) and (nTimeout > 0)):
        time.sleep(nTimeIncrement)
        nTimeout -= nTimeIncrement
    if (nTimeout > 0):
        nRes = 0
        # to do: make other checks
    if (nRes):
        tmpMsg = ssnMsg(destObj=destObj, srcObj=srcObj, msgType=msgType, msgID=msgID, msgData=msgData, \
        msgChannel=1, msgSocket=None, msgSerial = None)
    
        # Send data
        bufToSend = tmpMsg.getSSNPDU()
        print >> sys.stderr, 'sending "%s"' % bufToSend
        
#        print >> sys.stderr, 'publish to "%s"' % TOPIC_COMMANDS
        client.publish("/ssn/acc/"+str(ACCOUNT)+"/obj/"+str(destObj)+"/commands", payload=bufToSend, qos=0, retain=False)
    # to do: get response

#        recv_data = sock.recv(TCPBufferSize)
#        amount_received += len(recv_data)
#        print >>sys.stderr, 'received "%s"' % recv_data
    else:
        print >> sys.stderr, 'error connect to broker'
    

         
if __name__ == "__main__":
   main(sys.argv[1:])
