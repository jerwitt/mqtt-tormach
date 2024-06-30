import os
import time
import re
import paho.mqtt.client as mqtt

# mqtt settings
MQTT_BROKER = '192.168.1.10'
MQTT_BROKER_PORT = 1883
MQTT_TOPIC_INTERP = 'node_lathe/interp_state'
MQTT_TOPIC_STATUS_TASK_MODE = 'node_lathe/status/task_mode'
MQTT_TOPIC_STATUS_TASK_STATE = 'node_lathe/status/task_state'

# Logging setup
# Look for specific log lines that match an expected style we are interested in
class Log():
  LOG_FMT = re.compile(r'^(.+) \| (.*) \[(.+)\]')
  MSG_FMTS = [
      (re.compile(r'^LinuxCNC interp_state change was (.+) is now (.+)'), MQTT_TOPIC_INTERP, 2),
      (re.compile(r'^ensure_mode: changing LCNC mode to (.+)'), MQTT_TOPIC_STATUS_TASK_MODE, 1),
      (re.compile(r'^LinuxCNC status.task_mode change was (.+) is now (.+)'), MQTT_TOPIC_STATUS_TASK_MODE, 2),
      (re.compile(r'^status.task_state was (.+) is now (.+)'), MQTT_TOPIC_STATUS_TASK_STATE, 2)
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
          l.payload = mf.group(f[2])
          return l
    return None
  def __init__(self):
    self.date = None
    self.message = None
    self.source = None
    self.topic = None
    self.payload = None

#setup MQTT Client
def on_connect(client, userdata, flags, rc):
  pass
def on_publish(client, userdata, mid):
  pass
# client = mqtt.Client(client_id=__file__) # JW
client = mqtt.Client(client_id="e5c_15L")
client.on_connect = on_connect
client.on_publish = on_publish
client.connect(MQTT_BROKER, MQTT_BROKER_PORT, 60)

# Main program loop, run forever
LOG_FILE = '/home/operator/gcode/logfiles/pathpilotlog.txt'
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
          if (lc - lp) >= 60: client.reconnect()
          print('sending %s: %s' % (l.topic, l.payload), flush=True)
          client.publish(l.topic, l.payload, 2, False)
          lp = lc
        line = f.readline()
  lc += 1
  time.sleep(1)
