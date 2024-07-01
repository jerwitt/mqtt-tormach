import os
import random
import time
import re
import socket

import paho.mqtt.client as mqtt

# mqtt settings
MQTT_BROKER = '192.168.1.10'
MQTT_BROKER_PORT = 1883
random_id = str(random.randint(0,1000))
MQTT_CLIENTID = 'e5c_Laser-' + random_id
MQTT_TOPIC_FIBER = 'node_laser'

# LightBurn interface via UDP Socket
UDP_OUT_IP = "192.168.1.26"
UDP_OUT_PORT = 19840
UDP_IN_IP = "192.168.1.22"
UDP_IN_PORT = 19841
UDP_IN_TIMEOUT = 15

# Lightburn has very basic Protocol over UDP
# MESSAGE = "LOADFILE:C:\\test2.ai"
# MESSAGE = "FORCELOAD:C:\\test2.png"
# MESSAGE = "CLOSE"     # app close w/ dialog
# MESSAGE = "FORCECLOSE"
# MESSAGE = "START"     # start a laser cycle
# MESSAGE = "STATUS"    #jw 'OK' when IDLE,  '!' when "BUSY" (lasering or modal dialog)
# MESSAGE = "PING"      # is app running?
# MESSAGE = "IMPORT:"    #jw assume this is used to imports svg on top of template file?
# MESSAGE = "DGRect:"    #jw not sure this is even a command. maybe it draws alignment square
MESSAGE = "STATUS"



# Remap dict for incoming EVENT names to CLEANER VERSIONS
# simple event + data model
event_remap = {
    'INTERP_IDLE': 'IDLE',
    'INTERP_WAITING': 'WAIT',
    'INTERP_READING': 'RUN',
    'INTERP_PAUSED': 'PAUSE',
    'MODE_AUTO' : 'AUTO',
    'MODE_MANUAL' : 'MANUAL',
    'MODE_MDI' : 'MDI',
    # 'pressed': 'BUTTON',
    'cycle_start': 'CYCLE_START',
    'back_button': 'BACK',
    'reset': 'RESET',
    'stop': 'STOP',
    'Loading': 'LOAD'
}


# Logging setup
# Look for specific log lines that match an expected style we are interested in
class Log():
    LOG_FMT = re.compile(r'^(.+) \| (.*) \[(.+)]')

    # Parse into: "Search Text (.+)", TOPIC PATH, Which (.+) has the 'event', which (.+) has data, "extra data formatter"
    MSG_FMTS = [
#        (re.compile(r'^LinuxCNC interp_state change was (.+) is now (.+)'), MQTT_TOPIC_INTERP, 2, 0, ""),
#        (re.compile(r'^ensure_mode: changing LCNC mode to (.+)'), MQTT_TOPIC_STATUS_TASK_MODE, 1, 0, ""),
#        (re.compile(r'^LinuxCNC status.task_mode change was (.+) is now (.+)'), MQTT_TOPIC_STATUS_TASK_MODE, 2, 1," <- "),
#        (re.compile(r'^status.task_state was (.+) is now (.+)'), MQTT_TOPIC_STATUS_TASK_STATE, 2, 0, ""),
#        (re.compile(r'^(.+) G code: (.+)'), MQTT_TOPIC_LOADING, 1, 2, " "),
#        (re.compile(r'^(.+) button was (.+)'), MQTT_TOPIC_BUTTON_PRESS, 1, 2, " ")
    ]

    def create(line: str):
        m = re.match(Log.LOG_FMT, line)
        if m:
            l = Log()
            l.date = m.group(1)
            l.message = m.group(2)
            l.source = m.group(3)
            for f in Log.MSG_FMTS:
                mf = re.match(f[0], l.message)
                if mf:
                    l.topic = f[1]
                    event_name = mf.group(f[2])
                    event_data_prepend = f[4]
                    event_data = mf.group(f[3])

                    # remap the words as necessary
                    for search,replace in event_remap.items():
                        if event_name == search:
                            event_name = replace

                    if f[3] != 0:
                        l.payload = event_name + event_data_prepend + event_data
                    else:
                        l.payload = event_name
                    return l
        return None


    def __init__(self):
        self.date = None
        self.message = None
        self.source = None
        self.topic = None
        self.payload = None

# END LOG() CLASS

#setup MQTT Client
def on_connect(client, userdata, flags, rc):
    print("onconnect called")


def on_publish(client, userdata, mid):
    print("publish called")


def connect_mqtt():
    # client.set_callback(sub_cb)
    def on_connect(client, userdata, flags, rc):
        if (rc == 0):
            print("Connected!")
        else:
            print("Failed rc=%d\n", rc)

    client = mqtt.Client(MQTT_CLIENTID)
    client.on_connect = on_connect
    client.connect(MQTT_BROKER, MQTT_BROKER_PORT)
    return client


# Main program
client = connect_mqtt()
client.loop_start()

lc = 0
lp = 0

# Open UDP to Sockets to Lightburn IN/OUT
outSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
inSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
inSock.settimeout(15)
inSock.bind((UDP_IN_IP, UDP_IN_PORT))
l = Log()
l.topic = MQTT_TOPIC_FIBER

#loop forever
while True:
    try:
        outSock.sendto((MESSAGE).encode(), (UDP_OUT_IP, UDP_OUT_PORT))
        data, addr = inSock.recvfrom(1024)
        print (data)
        if data == b'OK':
            l.payload = "IDLE"
        else:
            l.payload = "BUSY"
        if l:
            if (lc - lp) >= 60:
                print ("reconnect broker")
                client.reconnect()

            print('sending %s: %s' % (l.topic, l.payload), flush=True)
            client.publish(l.topic, l.payload, 2, False)
            lp = lc
    except:
        print ("reopen sockets")
        # open_sockets(outSock, inSock)
        outSock.close()
        inSock.close()
        outSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        inSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # outSock.settimeout(60)
        inSock.settimeout(UDP_IN_TIMEOUT)
        inSock.bind((UDP_IN_IP, UDP_IN_PORT))
        l.payload = f"OFFLINE {(lc-lp)*UDP_IN_TIMEOUT}s"
        client.publish(l.topic, l.payload, 2, False)
    lc += 1
    time.sleep(1)


