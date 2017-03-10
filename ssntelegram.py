import sys
import time
import telepot
#import json
import string
#import paho.mqtt.client as mqtt
import datetime
import threading
from ssn import ssnMsg

class ssnTlg(object):

    def __init__(self, strTOKEN,  ssnGrp="", acc = 0, client=None, tlg_obj = 0):
        self.TOKEN = strTOKEN
        self.ssnGrp = ssnGrp
        self.acc = acc
        self.client = client
        self.bot = telepot.Bot(self.TOKEN)
        self.answerer = telepot.helper.Answerer(self.bot)
        self.tlg_obj = tlg_obj
        try:
#            self.bot.message_loop(self.handle)
            self.bot.message_loop({'chat': self.on_chat_message,
                  'edited_chat': self.on_edited_chat_message,
                  'callback_query': self.on_callback_query,
                  'inline_query': self.on_inline_query,
                  'chosen_inline_result': self.on_chosen_inline_result})
            print 'Telegram bot listening ...'
        except Exception, e:
                print("Telegram notification error"+str(e), "e")

    def sendSsnMessage(self, msg, obj_id = 0, dev = 0, ch = 0):
        if (self.client):
            try:
                self.client.publish("/ssn/acc/"+str(self.acc)+"/obj/"+
                str(obj_id)+"/device/"+str(dev)+"/"+str(ch)+"/out", payload=msg, qos=0, retain=False)
            except Exception, e:
                print("Error publishing message"+str(e), "e")

    def sendSsnCommand(self, msg, obj_id = 0):
        if (self.client):
            try:
                self.client.publish("/ssn/acc/"+str(self.acc)+"/obj/"+
                str(obj_id)+"/commands", payload=msg, qos=0, retain=False)
                print ("publish command: "+msg)
            except Exception, e:
                print("Error publishing message"+str(e), "e")
                
    def sendTlgMessage(self, msg, chat_id = None):
        if (chat_id):
            self.bot.sendMessage(chat_id, msg)
        else:
            self.bot.sendMessage(self.ssnGrp, msg)

    def sendTlgPhoto(self, photo, chat_id = None):
        f = open("/tmp/photo_tmp.jpg", "wb")
        f.write(photo)
        f.close()
        f = open("/tmp/photo_tmp.jpg", "rb")
        if (chat_id):
            self.bot.sendPhoto(chat_id, f)
        else:
            self.bot.sendPhoto(self.ssnGrp, f)
        f.close()

    def on_edited_chat_message(self, msg):
        content_type, chat_type, chat_id = telepot.glance(msg, flavor='edited_chat')
        print('Edited chat:', content_type, chat_type, chat_id)

#    def handle(self, msg):
    def on_chat_message(self, msg):
        content_type, chat_type, chat_id = telepot.glance(msg)
        print('Chat:', content_type, chat_type, chat_id)
        msg_text = ""

        content_type, chat_type, chat_id = telepot.glance(msg)
        try:
#                msg_data = json.loads(msg)
            if (len(msg)):
                msg_text = msg["text"]
                cmdArray = string.rsplit(msg_text,' ')
                command = cmdArray[0]
                if (len(command)):
                    print ("command: "+command)
                    if (command == "/getdevvals"):
                        obj = cmdArray[1]
#                            if (isinstance( a,( int, long ) )
                        if (obj.isdigit()):
                            ssn_cmd = '{"ssn":{"v":1,"obj":'+obj+',"cmd":"getdevvals", "data": {"g":1}}}'
#                            ssn_cmd = '===ssn10001000502003b{"ssn":{"v":1,"obj":'+int(cmdArray[1])+',"cmd":"getdevvals", "data": {"g":1}}}968f' # !!!!!!!!TO DO
#                                tmpMsg = ssnMsg(destObj=int(obj), srcObj=self.tlg_obj, msgType=2, msgID=None, msgData=ssn_cmd)
                            tmpMsg = ssnMsg(destObj=10, srcObj=5, msgType=2, msgID=None, msgData=str(ssn_cmd))
                            print tmpMsg.getSSNPDU()
                            self.sendSsnCommand(msg = tmpMsg.getSSNPDU(), obj_id = int(obj))
                        else:
                            self.bot.sendMessage(chat_id, "ERROR: OBJ_ID not integer"+obj)

#    sdv = '{"ssn":{"v":1,"obj":'+obj+',"cmd":"sdv", "data": {"adev":'+dev+',"acmd":'+ch+',"aval":'+msg.payload+'}}}"'

                    elif (command == "/info"):
                        self.bot.sendMessage(chat_id, "INFO: MQTTHOST"+self.client._host)
                    elif (command == "/unixtime"):
                        self.sendTlgMessage("MSK-1: "+datetime.datetime.utcfromtimestamp(int(cmdArray[1])).strftime('%Y-%m-%d %H:%M:%S'), chat_id)
#                            self.bot.sendMessage(chat_id, "MSK-1: "+datetime.datetime.utcfromtimestamp(int(cmdArray[1])).strftime('%Y-%m-%d %H:%M:%S'))
 
        except Exception as ex:
            print("Exception message processing, msg={}: {}".format(msg,ex))

        print('Normal Message:', content_type, chat_type, chat_id)
#	    self.bot.sendMessage(chat_id, msg_text)
#        show_keyboard = {'keyboard': [['Yes','No'], ['Maybe','Maybe not']]}
#        bot.sendMessage('-123873656', 'This is a custom keyboard', reply_markup=show_keyboard)

    def on_callback_query(self, msg):
        query_id, from_id, data = telepot.glance(msg, flavor='callback_query')
        print('Callback query:', query_id, from_id, data)
    
        if data == 'notification':
            self.bot.answerCallbackQuery(query_id, text='Notification at top of screen')
        elif data == 'alert':
            self.bot.answerCallbackQuery(query_id, text='Alert!', show_alert=True)
        elif data == 'edit':
            global message_with_inline_keyboard
    
            if message_with_inline_keyboard:
                msg_idf = telepot.message_identifier(message_with_inline_keyboard)
                self.bot.editMessageText(msg_idf, 'NEW MESSAGE HERE!!!!!')
            else:
                self.bot.answerCallbackQuery(query_id, text='No previous message to edit')
    
    def on_inline_query(self, msg):
        def compute():
            query_id, from_id, query_string = telepot.glance(msg, flavor='inline_query')
            print('%s: Computing for: %s' % (threading.current_thread().name, query_string))
        self.answerer.answer(msg, compute)

    def on_chosen_inline_result(self, msg):
        result_id, from_id, query_string = telepot.glance(msg, flavor='chosen_inline_result')
        print('Chosen Inline Result:', result_id, from_id, query_string)

   


# ============================================================================
if __name__ == "__main__":
    myTOKEN = sys.argv[1]  # get token from command-line
    myGrp = sys.argv[2]  # get GRP from command-line

    ssnbot = ssnTlg(myTOKEN, myGrp) 

    # Keep the program running.
    while 1:
        time.sleep(10)
