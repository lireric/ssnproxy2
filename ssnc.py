#!/usr/bin/env python
from ssnproxy import ssnMsg, config
import socket
import sys, getopt

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
       print 'ssnc.py [--file <inputfile> or -D <data string>] --dest <destObj> -src <srcObj> --type <msgType> --id <msgID>'
       sys.exit(2)
    for opt, arg in opts:
       if opt == '-h':
           print 'ssnc.py [--file <inputfile> or -D <data string>] --dest <destObj> -src <srcObj> --type <msgType> --id <msgID>'
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

    TCPBufferSize = config["TCPBufferSize"]
    REMOTE_HOST = config["REMOTE_HOST"]         # Symbolic name meaning all available interfaces
    PORT = config["PORT"]        # TCP port 

# Create a TCP/IP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    tmpMsg = ssnMsg(destObj=destObj, srcObj=srcObj, msgType=msgType, msgID=msgID, msgData=msgData, \
    msgChannel=1, msgSocket=sock, msgSerial = None)

    bufToSend = tmpMsg.getSSNPDU()


# Connect the socket to the port where the server is listening
    server_address = (REMOTE_HOST, PORT)
    print >>sys.stderr, 'connecting to %s port %s' % server_address
    sock.connect(server_address)

    try:
    # Send data
        print >>sys.stderr, 'sending "%s"' % bufToSend
        sock.sendall(bufToSend)

    # Look for the response
        amount_received = 0
    
        recv_data = sock.recv(TCPBufferSize)
        amount_received += len(recv_data)
        print >>sys.stderr, 'received "%s"' % recv_data

    finally:
        print >>sys.stderr, 'closing socket'
        sock.close()
        
if __name__ == "__main__":
   main(sys.argv[1:])
