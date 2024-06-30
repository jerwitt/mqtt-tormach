import os
import random
import time
import re
from typing import Dict

import paho.mqtt.client as mqtt

# mqtt settings
MQTT_BROKER = '192.168.1.10'
MQTT_BROKER_PORT = 1883
random_id = str(random.randint(0,1000))
MQTT_CLIENTID = 'e5c_Lathe-' + random_id
#MQTT_CLIENTID = e5c_Lathe-{random.randint(0, 1000)}'
#MQTT_TOPIC_INTERP = 'node_lathe/interp_state'
#MQTT_TOPIC_STATUS_TASK_MODE = 'node_lathe/status/task_mode'
#MQTT_TOPIC_STATUS_TASK_STATE = 'node_lathe/status/task_state'
MQTT_TOPIC_INTERP = 'node_lathe'
MQTT_TOPIC_STATUS_TASK_MODE = 'node_lathe'
MQTT_TOPIC_STATUS_TASK_STATE = 'node_lathe'
MQTT_TOPIC_LOADING = 'node_lathe'
MQTT_TOPIC_BUTTON_PRESS = 'node_lathe'

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
        (re.compile(r'^LinuxCNC interp_state change was (.+) is now (.+)'), MQTT_TOPIC_INTERP, 2, 0, ""),
#        (re.compile(r'^ensure_mode: changing LCNC mode to (.+)'), MQTT_TOPIC_STATUS_TASK_MODE, 1, 0, ""),
        (re.compile(r'^LinuxCNC status.task_mode change was (.+) is now (.+)'), MQTT_TOPIC_STATUS_TASK_MODE, 2, 1,
         " <- "),
        (re.compile(r'^status.task_state was (.+) is now (.+)'), MQTT_TOPIC_STATUS_TASK_STATE, 2, 0, ""),
        (re.compile(r'^(.+) G code: (.+)'), MQTT_TOPIC_LOADING, 1, 2, " "),
        (re.compile(r'^(.+) button was (.+)'), MQTT_TOPIC_BUTTON_PRESS, 1, 2, " ")
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

    def remap(self):
        for row in rows:
            row = {name_map[name]: val for name, val in row.items()}

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


client = connect_mqtt()
client.loop_start()

# Main program loop, run forever
try:
    LOG_FILE = '/home/operator/gcode/logfiles/pathpilotlog.txt'
    s = os.stat(LOG_FILE)
except:
    print ("PathPilot Log file not found. Falling back to local p_new.txt")
    LOG_FILE = './p_new.txt'   # used for local testing
    try:
        s = os.stat(LOG_FILE)
    except:
        print ("p_new.txt not found creating")
        open('p_new.txt', 'w')
        s = os.stat(LOG_FILE)
lc = 0
lp = 0
while True:
    _s = os.stat(LOG_FILE)
    if _s.st_mtime != s.st_mtime:
        size = (_s.st_size - s.st_size)
        seek = s.st_size
        s = _s
        if size < 0:
            # log was rotated, read everything
            seek = 0
        with open(LOG_FILE) as f:
            f.seek(seek)
            line = f.readline()
            while line:
                l = Log.create(line)
                if l:
                    if (lc - lp) >= 60:
                        client.reconnect()
                    print('sending %s: %s' % (l.topic, l.payload), flush=True)
                    client.publish(l.topic, l.payload, 2, False)
                    lp = lc
                line = f.readline()
    lc += 1
    time.sleep(1)
