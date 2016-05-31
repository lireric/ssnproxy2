# -*- coding: utf-8 -*-
"""
Created on Mon Mar  7 21:39:17 2016

@author: eric@mail.ru
"""
from datetime import datetime
#import crc16
from PyCRC.CRCCCITT import CRCCCITT
import string
import struct
import sys

cSSNSTART = "===ssn1" #ssn packet template


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
        self.srcObj,self.msgType,len(self.msgData),self.msgData,CRCCCITT(version="FFFF").calculate(self.msgData))
#        self.srcObj,self.msgType,len(self.msgData),self.msgData,crc16.crc16xmodem(self.msgData, 0xffff))
        return buf

    # scan text buffer and try to parse SSN message format:
    def processBuffer(self, buf):
        bufTail = ""
        nResult = False     # success or not result
        
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
                        calcCRC = CRCCCITT(version="FFFF").calculate(pduData)
#                        calcCRC = crc16.crc16xmodem(pduData, 0xffff)
                        pduCRC = int(pduCRC, 16)
                        if (calcCRC == pduCRC):
                            self.destObj=destObj
                            self.srcObj=srcObj
                            self.msgType=msgType
                            self.msgID=None
                            self.msgData=pduData
    #                        routeMessage(tmpMsg)
                            currentPos = pduDataPos+packetLen+4
                            nResult = True
                        else:
#                            logWrite("CRC Error! dest[{}] src[{}] msg[{}...]".format(destObj,srcObj,pduData[0:20]))
                            print >> sys.stderr, "CRC Error! dest[{}] src[{}] msg[{}...]".format(destObj,srcObj,pduData[0:20])
                            currentPos = pduDataPos+packetLen+4
                except Exception, e:
                    currentPos = pduPos + 14
                    bufTail = buf[currentPos:]
                    print >> sys.stderr, "Error processing SSN PDU"+str(e)
            else:
                if (currentPos < 0):
                    bufTail = ""
                else:
                    bufTail = buf[currentPos:]
        return bufTail, nResult
