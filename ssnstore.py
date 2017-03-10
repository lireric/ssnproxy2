#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Created on Tue Apr 26 23:03:00 2016

@author: eric
"""
import logging
import logging.handlers
import sys
import string
import datetime
import json
import paho.mqtt.client as mqtt
import pymongo
HAVE_TLS = True
try:
    import ssl
except ImportError:
    HAVE_TLS = False


# The callback for when a PUBLISH message is received from the server from /ssn/acc/ACCOUNT/obj/+/device/+/+/out topic.
def chvalue_callback(client, userdata, msg):
    global db, ACCOUNT
#    print(str(datetime.now()) + " " + "chvalue: "+msg.topic+"->"+msg.payload)
    logger1.info("chvalue: "+msg.topic+"->"+msg.payload)
    topicArray = string.rsplit(msg.topic,'/')
    dev = topicArray[len(topicArray)-3]
    ch = topicArray[len(topicArray)-2]
    obj = topicArray[len(topicArray)-5]
    try:
        db.dev_values.insert({"ts":datetime.datetime.utcnow(), "acc":ACCOUNT,
                              "obj":int(obj, 10), "dev":int(dev, 10), "ch":int(ch, 10), "val":int(msg.payload, 10)})
    except Exception as ex:
#        print("MongoDB error={}: {}".format(msg.payload,ex))
        logger1.error("MongoDB error={}: {}".format(msg.payload,ex))

# The callback for when a PUBLISH message is received from the server from /ssn/acc/ACCOUNT/obj/+/device/+/+/out topic.
def event_callback(client, userdata, msg):
    global db
#    print(str(datetime.now()) + " " + "event: "+msg.topic+"->"+msg.payload)
    logger1.info("event: "+msg.topic+"->"+msg.payload)
    topicArray = string.rsplit(msg.topic,'/')
    obj = topicArray[len(topicArray)-2]
    # {"a": 0, "c": 3, "t": 1432600485, "d": 1004, "v": 3238}
    try:
        e_data = json.loads(msg.payload)
        # log only action events:
        if (e_data["a"]):
            try:
                db.events.insert_one({"ts":datetime.datetime.utcnow(), "acc":ACCOUNT, "tt":e_data["t"],
                    "obj":int(obj, 10), "dev":e_data["d"], "ch":e_data["c"],
                    "val":e_data["v"], "act":e_data["a"]})
            except Exception as ex:
#                print("MongoDB error={}: {}".format(e_data,ex))
                logger1.error("MongoDB error={}: {}".format(e_data,ex))
    except Exception as ex:
#        print("Cannot decode JSON object, payload={}: {}".format(msg.payload,ex))
        logger1.warn("Cannot decode JSON object, payload={}: {}".format(msg.payload,ex))
                    
# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
#    print("Connected with result code "+str(rc))
    logger1.info("Connected with result code "+str(rc))

    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    client.subscribe([("/ssn/acc/"+str(ACCOUNT)+"/obj/+/events", 0),
                      ("/ssn/acc/"+str(ACCOUNT)+"/obj/+/device/+/+/out", 0)])



# ---------------------------------------------- globals:
config = {}
execfile("ssnmqtt.cfg", config)
SSNDB_HOST = config["SSNDB_HOST"]     # ssn database host
SSNDB_PORT = config["SSNDB_PORT"]     # ssn database port 
SSNDB_USER = config["SSNDB_USER"]     # ssn database user
SSNDB_PASS = config["SSNDB_PASS"]     # ssn database password
SSNDB_DBNAME = config["SSNDB_DBNAME"] # ssn database name

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

ACCOUNT = config["ACCOUNT"]


# ============================================================================
if __name__ == "__main__":
    logger1 = logging.getLogger('ssnstore')
    logger1.setLevel(logging.INFO)
    # create syslog handler
    slh = logging.handlers.SysLogHandler(address = '/dev/log')
    # create console handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)

    formatter = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')
    slh.setFormatter(formatter)
    ch.setFormatter(formatter)
    logger1.addHandler(slh)
    logger1.addHandler(ch)

    client = mqtt.Client(client_id=MQTT_BROKER_CLIENT_ID)
    client.on_connect = on_connect

    client.chvalue_callback = chvalue_callback
    client.message_callback_add("/ssn/acc/"+str(ACCOUNT)+"/obj/+/device/+/+/out", chvalue_callback)

    client.event_callback = event_callback
    client.message_callback_add("/ssn/acc/"+str(ACCOUNT)+"/obj/+/events", event_callback)

    
    if (MQTT_BROKER_USER):
        client.username_pw_set(MQTT_BROKER_USER, password=MQTT_BROKER_PASS)

    if (HAVE_TLS and MQTT_BROKER_USE_TLS == 1):
# -- use TLS    
#        print "Use TLS"
        logger1.info("Use TLS")
        client.tls_set(MQTT_BROKER_CA_CERTS, certfile=MQTT_BROKER_CERTFILE, keyfile=MQTT_BROKER_KEYFILE, cert_reqs=ssl.CERT_REQUIRED,
            tls_version=ssl.PROTOCOL_TLSv1, ciphers=None)
        client.tls_insecure_set(True)
    else:
# -- use login/passw    
#        print "Use login/passw"
        logger1.info("Use login/passw")
    
    try:
        client.connect(MQTT_HOST, MQTT_PORT, 60)
    except Exception, e:
#        print("Cannot connect to MQTT broker at %s:%d: %s" % (MQTT_HOST, MQTT_PORT, str(e)))
        logger1.info("Cannot connect to MQTT broker at %s:%d: %s" % (MQTT_HOST, MQTT_PORT, str(e)))
        sys.exit(2)
    

#    client.username_pw_set(MQTT_BROKER_USER, password=MQTT_BROKER_PASS)
#    client.connect(MQTT_HOST, MQTT_PORT, 60)
 
    db_client = pymongo.MongoClient(SSNDB_HOST, SSNDB_PORT)
# to do: db user/pass
    db = db_client[SSNDB_DBNAME]
    
    # Blocking call that processes network traffic, dispatches callbacks and
    # handles reconnecting.
    # Other loop*() functions are available that give a threaded interface and a
    # manual interface.
    client.loop_forever()
