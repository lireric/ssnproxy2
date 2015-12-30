#!/usr/bin/env python
from threading import Thread
from Queue import Queue
#from struct import *
import struct
import string
import time
import serial
import crc16
import socket, threading
#import sys
from datetime import datetime, timedelta
#import signal, os
#import ConfigParser
#import struct

# ********************** common preferences:
SerialTimeout=1           #set a timeout value, None for waiting forever
TCPTimeout=2           #set a timeout value, None for waiting forever
CommonTimeout = 5
#Serialbaudrate=57600
#SerialPort='/dev/ttyUSB0'
#SerialBufferSize=1000
#TCPBufferSize=10000
#HOST = "0.0.0.0"         # Symbolic name meaning all available interfaces
#PORT = 10000        # TCP port 
logQueue = Queue()
msgArray = []       # messages in processing
objRoutes = {}

"""
"routes":[
{"obj":1,"if":1},
{"obj":3,"if":1}
],

"""

class Enum(tuple): __getattr__ = tuple.index

class ssnMsg(object):
    def __init__(self, destObj=0,  srcObj=0, msgType=None, msgID=None, \
    msgData=None, msgChannel=None, msgSocket=None, msgSerial=None):
        self.destObj = destObj
        self.srcObj = srcObj
        self.msgType = msgType
        self.msgID = msgID # message ID (from external system)
        self.msgData = msgData
        self.msgChannel = msgChannel # 0 - serial, 1 - TCP
        self.socket = msgSocket # client socket (for TCP channel) or None
        self.msgSerial = msgSerial
        self.msgTimestamp = datetime.now()
    def getSSNPDU(self):
        buf = "{}{:04x}{:04x}{:02x}{:04x}{}{:04x}".format(cSSNSTART,self.destObj,\
        self.srcObj,self.msgType,len(self.msgData),self.msgData,crc16.crc16xmodem(self.msgData, 0xffff))
        return buf


def logQProc():
    while True:
        item = logQueue.get()
        print item
        logQueue.task_done()

def logWrite(logMsg, level='w'):
#    print datetime.now(), logMsg
    logQueue.put(str(datetime.now()) + " " + logMsg)
    return

#def TCPTimeoutHnd(signum, frame):
#    logWrite( 'Signal handler called with signal' + str(signum))
#    return

class TCPThread(threading.Thread):
    def __init__(self, ip, port, socket):
        threading.Thread.__init__(self)
        self.ip = ip
        self.port = port
        self.socket = socket
        logWrite( "[+] New thread started for "+ip+":"+str(port))

    def run(self):    
        # use self.socket to send/receive
        logWrite( "Connection from : "+self.ip+":"+str(self.port))
#        self.socket.send("\nWelcome to the server\n\n")
        data = "1"
        tail = ""
        if len(data):
            data = tail + self.socket.recv(TCPBufferSize)
            logWrite( "Client sent : "+data)
            tail = processBuffer(data, channel=1, socket=self.socket)
#            self.socket.send("You sent me : "+data)
            time.sleep(TCPTimeout)
            try:
                if (self.socket):
                    self.socket.send("\nError: timeout\n\n")
                    self.socket.close()
                    logWrite( "TCPTimeout")
            except:
                logWrite( "socket error")
        logWrite( "Client disconnected...")

def getRouteInterface(destObj):
    destObjInterface = 0
    try:
        destObjInterface = objRoutes[destObj]
    except:
        destObjInterface = 0
        logWrite( "use defaut route")
    return destObjInterface

def sendMessage(ssnMessage, replyMessage = None):
    if (replyMessage):
        ssnMessage.destObj = replyMessage.srcObj
        ssnMessage.msgChannel = getRouteInterface(ssnMessage.destObj)
        ssnMessage.socket = replyMessage.socket
        logWrite( "reply to src:"+str(replyMessage.srcObj)+" channel: "+str(ssnMessage.msgChannel))
    else:
        ssnMessage.msgChannel = getRouteInterface(ssnMessage.destObj)
    # to do
    tmp_buff = ssnMessage.getSSNPDU()
    logWrite( "channel:"+str(ssnMessage.msgChannel)+" message to send: "+tmp_buff)

    if (ssnMessage.msgChannel == 0):
        # use serial interface
        ssnMessage.msgSerial.setRTS(True)
#        time.sleep(0.5)
        ssnMessage.msgSerial.write(tmp_buff)
        while (ssnMessage.msgSerial.outWaiting() > 0):
            time.sleep(0.01)
        ssnMessage.msgSerial.setRTS(False)
    if ((ssnMessage.msgChannel == 1) and (ssnMessage.socket)):
        # use TCP interface
        ssnMessage.socket.send(tmp_buff)
        ssnMessage.socket.close()
        ssnMessage.socket = None
    return
    
def routeMessage(ssnMessage):
    logWrite('routeMessage: dest[{}] src[{}] msg[{}...]'.format(ssnMessage.destObj, ssnMessage.srcObj, ssnMessage.msgData[0:20]))
    # check for async response:
    # 1. search message by msgID
    # 2. if not find by msgID let's try to search first message with that channel in array
    # 3. else send and add to array
    objUsedChannel = None
    isReplMessage = 0
    destObjInterface = getRouteInterface(ssnMessage.destObj)
#    ssnMessage.msgChannel = destObjInterface
    if (destObjInterface == 0):
        ssnMessage.msgSerial = ser1
    logWrite( "route message to interface: "+str(destObjInterface))
    for m in msgArray:
        # check for timeout
        msgLiveTime = datetime.now() - m.msgTimestamp
        if (msgLiveTime.total_seconds() > CommonTimeout):
            logWrite("Message timeout, remove from pool: "+str(msgLiveTime))
            msgArray.remove(m)
            next
        if (destObjInterface == m.msgChannel):
            objUsedChannel = m
            # if channel has message to same destination than skip processing
        if (ssnMessage.destObj == m.destObj):
            logWrite("Skip message processing: DestObj in pool")
            return
        if ((ssnMessage.msgID == m.msgID) and (m.msgID)):
         # if array consist message with this ID that our message is reply to it
            sendMessage(ssnMessage, m)
            isReplMessage = 1
            msgArray.remove(m)
            objUsedChannel = None
        # process broadcast message (dest = 0)
        if (ssnMessage.destObj == 0):
            # prevent resend message
            if (m.srcObj != ssnMessage.srcObj):
                objUsedChannel = m
    if (objUsedChannel):
        sendMessage(ssnMessage, objUsedChannel)
        isReplMessage = 1
        msgArray.remove(objUsedChannel)
    if (isReplMessage == 0):
        msgArray.append(ssnMessage)
        logWrite( "append new message to array. Current array size: "+str(len(msgArray))+" channel: "+str(destObjInterface))
        sendMessage(ssnMessage)
    return
    
def processBuffer(buf, socket=None, channel=None, ser=None):
    bufTail = ""
    if len(buf) > 0:
#        print "Read %i bytes:" % (len(buf))
        pduPos = string.find(buf,cSSNSTART)
        currentPos = pduPos
        if ((pduPos >= 0) and (len(buf)-pduPos)>=14):
# process SSN PDU
#/* -- SSN serial protocol description -----------------------------------------
# *
# * Format: "===ssn1DDDDSSSSTTLLLL...CCCC"
# *
# * ===ssn1 - start packet (protocol version 1)
# * DDDD - destination object (2 byte: hex chars - 0-9, A-F)
# * SSSS - source object (2 byte: hex chars - 0-9, A-F)
# * TT - message type (1 byte: hex chars - 0-9, A-F)
# * LLLL - packet length (2 byte: hex chars - 0-9, A-F)
# * ... data
# * CCCC - CRC16 (2 byte: hex chars - 0-9, A-F)
# *
# * data sending in ascii format
# * timeout = 2 sec
# *
# * */
            destObj, srcObj, msgType, packetLen = \
            struct.unpack_from('<4s4s2s4s', buf, pduPos + len(cSSNSTART))
            try:
            # convert to integers
                destObj = int(destObj, 16)
                srcObj = int(srcObj, 16)
                msgType = int(msgType, 16)
                packetLen = int(packetLen, 16)
                pduDataPos = pduPos + len(cSSNSTART)+14
                if ((pduDataPos+packetLen+4)<=len(buf)):
                    pduData = buf[pduDataPos:pduDataPos+packetLen]
                    pduCRC = struct.unpack_from('<4s', buf, pduDataPos+packetLen)[0]
                    calcCRC = crc16.crc16xmodem(pduData, 0xffff)
                    pduCRC = int(pduCRC, 16)
                    if (calcCRC == pduCRC):
                        tmpMsg = ssnMsg(destObj=destObj, srcObj=srcObj, msgType=msgType, msgID=None, msgData=pduData, msgChannel=channel, msgSocket=socket, msgSerial = ser)
                        routeMessage(tmpMsg)
                        currentPos = pduDataPos+packetLen+4
                    else:
                        logWrite("CRC Error! dest[{}] src[{}] msg[{}...]".format(destObj,srcObj,pduData[0:20]))
                        currentPos = pduDataPos+packetLen+4
                    # check buffer tail
                    if (currentPos < len(buf)):
                        logWrite("continue process buffer:"+buf[currentPos:])
                        bufTail = processBuffer(buf[currentPos:])
                    else:
                        bufTail = buf[currentPos:]
            except Exception, e:
                currentPos = pduPos + 14
                bufTail = buf[currentPos:]
                logWrite("Error processing SSN PDU"+str(e))
        else:
            if (currentPos < 0):
                bufTail = ""
            else:
                bufTail = buf[currentPos:]
    return bufTail

def listenerSerial(ser, queue):
    logWrite( "Serial listener started. Dev: "+ser.port)
    tail = ""
    while(1):
#        print "read.."
        ser.setRTS(False)
        buf = tail + ser.read(SerialBufferSize)
        if (buf):
            logWrite("BUF:"+buf)
#            logWrite("TAIL:"+tail)
        tail = processBuffer(buf, channel=0, ser=ser)
#            for i in buf:
#                value = struct.unpack('B', i)[0]
#                print "%02x" % (value),
    logWrite( "Exit serial")
    return

def listenerTCP(tcp1, queue):
#    s = None
    threads = []
    try:
        tcpsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    except socket.error as msg:
        logWrite(msg, 'e') 
    tcpsock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_address = (HOST,PORT)
    try:
        tcpsock.bind(server_address)
        while True:
            tcpsock.listen(2)
            logWrite( "Listening for incoming connections...")
            (clientsock, (ip, port)) = tcpsock.accept()
            newthread = TCPThread(ip, port, clientsock)        
            newthread.start()
            threads.append(newthread)
    except socket.error as msg:
        logWrite(str(msg), 'e') 
        tcpsock.close()
    for t in threads:
        t.join()
    return




# - - - - - main program:
cSSNSTART = "===ssn1" #ssn packet template
strTest = '===ssn100010003020033{"ssn":{"v":1,"cmd":"getowilist", "data": {"g":1}}}dfd3  ===ssn100050003020033{"ssn":{"v":1,"cmd":"getowilist", "data": {"g":1}}}dfd3 ===ssn10007'

"""
eLastCommandStatuses = Enum([\
'LC_NONE',              # /* not any data */ \             
'LC_SERIAL_CMD_SENT',   # /* command sent by serial (waiting response with data) */ \
'LC_TCP_CMD_SENT',      # /* command sent by TCP (waiting response with data) */ \
'LC_SERIAL_DATA_READY', # /* data load and ready to sent for serial */ \
'LC_SERIAL_DATA_ERROR', \
'LC_TCP_DATA_READY',    \
'LC_TCP_DATA_ERROR',    \
'LC_TIMEOUT_ERROR'      # /* fire on timeout on any interface */ \
])
nCurrentStatus = eLastCommandStatuses.LC_NONE # store last command status (ref. eLastCommandStatuses)
"""

config = {}
execfile("ssnproxy.cfg", config) 
# objects routing interfaces
serial_if = config["tcp_if"]
tcp_if = config["serial_if"]
Serialbaudrate=config["Serialbaudrate"]
SerialPort=config["SerialPort"]
SerialBufferSize=config["SerialBufferSize"]
TCPBufferSize=config["TCPBufferSize"]
HOST = config["HOST"]         # Symbolic name meaning all available interfaces
PORT = config["PORT"]        # TCP port 

for i in serial_if:
    objRoutes[i] = 1
for i in tcp_if:
    objRoutes[i] = 0
 
ser1 = serial.Serial(
    port=SerialPort,
    baudrate=Serialbaudrate,
    timeout=SerialTimeout,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    rtscts = True,
    bytesize=serial.EIGHTBITS
)

ser1.setRTS(False)

tcp1 = '' # to do

# ============================================================================
if __name__ == "__main__":
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
    workerTCP = Thread(target=listenerTCP, args=(tcp1, queue))
    workerTCP.setDaemon(True)
    workerTCP.start()

    while(1):
        time.sleep(1)
        
    workerSerial.join
    workerTCP.join