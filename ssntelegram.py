import sys
import time
import telepot
import json
import string
import paho.mqtt.client as mqtt


class ssnTlg(object):
    def __init__(self, strTOKEN,  ssnGrp="", acc = 0, client=None):
        self.TOKEN = strTOKEN
        self.ssnGrp = ssnGrp
        self.acc = acc
        self.client = client
        self.bot = telepot.Bot(self.TOKEN)
        answerer = telepot.helper.Answerer(self.bot)

        self.bot.notifyOnMessage(self.handle)
        print 'Listening ...'

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

    def handle(self, msg):
        flavor = telepot.flavor(msg)
        msg_text = ""
        articles = [{'type': 'article',
                    'id': 'abc', 'title': 'ABC', 'message_text': 'Good morning'}]

        # normal message
        if flavor == 'normal':
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
                            ssn_cmd = '===ssn10001000502003b{"ssn":{"v":1,"obj":1,"cmd":"getdevvals", "data": {"g":1}}}968f'
                            self.sendSsnCommand(msg = ssn_cmd, obj_id = 1)
 
            except Exception as ex:
                print("Cannot decode JSON object, msg={}: {}".format(msg,ex))

            print('Normal Message:', content_type, chat_type, chat_id)
	    self.bot.sendMessage(chat_id, msg_text)
#        show_keyboard = {'keyboard': [['Yes','No'], ['Maybe','Maybe not']]}
#        bot.sendMessage('-123873656', 'This is a custom keyboard', reply_markup=show_keyboard)

        # inline query - need `/setinline`
        elif flavor == 'inline_query':
            query_id, from_id, query_string = telepot.glance(msg, flavor=flavor)
            print('Inline Query:', query_id, from_id, query_string)
            self.bot.answerInlineQuery(query_id, articles)

    # Do your stuff according to `content_type` ...
        # chosen inline result - need `/setinlinefeedback`
        elif flavor == 'chosen_inline_result':
            result_id, from_id, query_string = telepot.glance(msg, flavor=flavor)
            print('Chosen Inline Result:', result_id, from_id, query_string)

        # Remember the chosen answer to do better next time

        else:
            raise telepot.BadFlavor(msg)

        # Compose your own answers

        print (msg)


# ============================================================================
if __name__ == "__main__":
    myTOKEN = sys.argv[1]  # get token from command-line
    myGrp = sys.argv[2]  # get GRP from command-line

    ssnbot = ssnTlg(myTOKEN, myGrp) 

    # Keep the program running.
    while 1:
        time.sleep(10)
