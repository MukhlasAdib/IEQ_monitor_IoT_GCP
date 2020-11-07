import datetime
import json
import os
import ssl
import time
import jwt
import paho.mqtt.client as mqtt
import json
import numpy as np
from http.server import HTTPServer
from http.server import BaseHTTPRequestHandler
import urllib.parse
import pickle

### Common Variables
jwt_alg = 'RS256'
ca_certs = 'roots.pem'
fdate = ''
num = 1
fname = ''
gw_DEVID = 'DEV001'
GWYID = 'GWY001'
dev_keyDir = 'device_key/'
dev_metaDir = 'device_list/'
attachedDev = {}
sampling_freq = 15
live_log = []
max_live_log = 20

### Variables for GCP connection
gw_private = 'rsa_private.pem'
project_id = 'tactical-patrol-276605'
gcp_region = 'asia-east1'
gcp_hostname = 'mqtt.googleapis.com'
gcp_port = 8883
gw_registyID = 'tugas_scada_tim7_testReg'
gateway_id = 'tugas_scada_tim7_gwy001'

### Variables for Local Connection
local_hostname = 'localhost'
local_port = 1883
local_data_topic = 'GWY/data'
local_state_topic = 'GWY/state'

### Common functions
def renew_filename():
    # Create new filename for logging
    global fdate
    global num
    global fname
    now = datetime.datetime.now()
    fdate = now.strftime("%Y%m%d")
    num = 1
    if not os.path.exists('log'):
        os.makedirs('log')
    for file in os.listdir('log/'):
        if file.endswith('_test1_log.txt') and file.startswith(fdate):
            fnum = file.split('_')[1]
            num = int(fnum) + 1
    fname = 'log/' + fdate + '_' + str(num) + '_test1_log.txt'
renew_filename()

def create_jwt(project_id, private_key_file, algorithm):
    # Create a JWT to establish an MQTT connection.
    token = {
        'iat': datetime.datetime.utcnow(),
        'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=60),
        'aud': project_id
    }
    with open(private_key_file, 'r') as f:
        private_key = f.read()
    return jwt.encode(token, private_key, algorithm=algorithm)

def error_str(rc):
    # Convert a Paho error to a human readable string.
    return '{}: {}'.format(rc, mqtt.error_string(rc))

def add_log(msg):
    # Add log history
    now = datetime.datetime.now()
    date_time = now.strftime("%d-%m-%Y, %H:%M:%S")
    logStr = date_time + '\n'
    logStr = logStr + str(msg) + '\n'
    print(logStr)
    fdate_new = now.strftime("%Y%m%d")
    if fdate_new != fdate:
        renew_filename()
    with open(fname, "a") as f:
        f.write(logStr + '\n')

    live_log.append(logStr + '\n')
    if len(live_log) > max_live_log:
        live_log.pop(0)
    reporting()

def reporting():
    # Create live report HTML file to handle HTTP request
    msg = ''
    msg += 'LIVE REPORT OF ' + GWYID + '\n\n'
    msg += 'Attached devices:\n'
    for key,val in zip(attachedDev.keys(),attachedDev.values()):
        msg += key + ' : ' + val + '\n'
    msg += '\n'
    msg += 'Latest log:\n'
    for i,log in enumerate(live_log):
        msg += f'[{i+1}] ' + str(log)
    with open('live_log.txt','w') as f:
        f.write(msg)

### IEQ Data generator
class ieq_sim():
    def __init__(self):
        self.temp_sim = {'min':23.00,'max':30.00,'stdev':0.20}
        self.rh_sim = {'min':50.00,'max':80.00,'stdev':2.00}
        self.lux_sim = {'min':200,'max':300,'stdev':15}
        self.co2_sim = {'min':250,'max':500,'stdev':40}
        self.spl_sim = {'min':25,'max':45,'stdev':2}
        self.f = 2 * np.pi * 1/86400

    def calc(self,sim):
        # Calculate the new IEQ parameter
        now = datetime.datetime.now()
        midnight = now.replace(hour=0,minute=0,second=0,microsecond=0)
        today_second = (now - midnight).seconds
        val = (sim['max']+sim['min'])/2 - np.cos(self.f*today_second)*(sim['max']-sim['min'])/2
        val = np.random.normal(val,sim['stdev'])
        return val

    def gen_json(self):
        now = datetime.datetime.now()
        nowDate = now.strftime("%Y-%m-%d")
        nowTime = now.strftime("%H:%M:%S")
        ieq_dict = {
            'temp': round(self.calc(self.temp_sim),2),
            'rh': round(self.calc(self.rh_sim)),
            'lux': int(self.calc(self.lux_sim)),
            'co2': int(self.calc(self.co2_sim)),
            'spl': round(self.calc(self.spl_sim),2),
            'date': nowDate,
            'time': nowTime,
            'devID': gw_DEVID
        }
        jsonStr = json.dumps(ieq_dict)
        return jsonStr

### Handle connection to GCP MQTT
class mqtt_gcp():
    def __init__(self):
        self.local_handler = None
        self.isConnect = False
        # Set MQTT Client
        self.client = mqtt.Client(client_id = f'projects/{project_id}/locations/{gcp_region}/registries/{gw_registyID}/devices/{gateway_id}')
        self.client.tls_set(ca_certs=ca_certs, tls_version=ssl.PROTOCOL_TLSv1_2)
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_publish = self.on_publish
        self.client.on_subscribe = self.on_subscribe
        self.client.on_message = self.on_unknown_msg
        add_log('Connection to GCP Initiated')

    def connect(self):
        # Connect to GCP
        self.client.username_pw_set(
            username = 'unused',
            password = create_jwt(project_id,gw_private,jwt_alg))
        self.client.connect(gcp_hostname,gcp_port)
        add_log('Trying to connect to GCP')
        self.client.loop_start()
        self.wait_connect()
        gw_config_topic = f'/devices/{gateway_id}/config'
        subs_id = self.client.subscribe(gw_config_topic,1)
        add_log('GCP subscription request sent for topic ' + gw_config_topic + ' ID ' + str(subs_id[1]))

    def wait_connect(self,timeout = 10):
        total_time = 0
        while not self.isConnect and total_time < timeout:
            time.sleep(1)
            total_time += 1
        if not self.isConnect:
            logMsg = 'Cannot connect to GCP MQTT' 
            add_log(logMsg)
            return False
        else:
            return True

    def send_data(self,data):
        # Send data to GCP handle
        jsonData = json.loads(data)
        if 'devID' in jsonData:
            dev_num = jsonData['devID']
            deviceID = self.auth_device(dev_num)
            if deviceID:
                if not 'date' in jsonData:
                    jsonData['date'] = datetime.datetime.now().strftime("%Y-%m-%d")
                if not 'time' in jsonData:
                    jsonData['time'] = datetime.datetime.now().strftime("%H:%M:%S")
                jsonData['gwyID'] = GWYID
                new_data = json.dumps(jsonData)
                while not self.isConnect: self.connect()
                sendTopic = f'/devices/{deviceID}/events'
                res = self.client.publish(sendTopic, new_data, qos=1)
                logMsg = f'Publishing to GCP (ID {res.mid}) : \n' + str(new_data)
                add_log(logMsg)
            else:
                add_log('Unknown source\n' + data)
        else:
            add_log('Device info is not included\n' + data)

    def auth_device(self,dev_num):
        # Check whether the local device is known to gateway
        if dev_num in attachedDev:
            return attachedDev[dev_num]
        
        metaName = f'{dev_num}_meta.txt'
        if metaName in os.listdir(dev_metaDir):
            with open(dev_metaDir+metaName,"r") as f:
                json_meta = json.load(f)
        else: 
            add_log('Meta file not found\n' + metaName)
            return ''

        keyName = f'{dev_num}_rsa_private.pem'
        if not keyName in os.listdir(dev_keyDir):
            add_log('Private key not found\n' + keyName)
            return ''
        
        self.req_attachment(json_meta['ID'],dev_keyDir+keyName)
        attachedDev[dev_num] = json_meta['ID']
        return attachedDev[dev_num]

    def req_attachment(self,ID, keyFile):
        # Send vevice attachment request to GCP
        token = create_jwt(project_id,keyFile,jwt_alg)
        token = str(token)[2:-1]
        payload = '{\"authorization\":\"'+ token +'\"}'
        topic = f'/devices/{ID}/attach'
        res = self.client.publish(topic,payload,1)
        logMsg = f'Sending GCP attachment request for {ID} with message ID {res.mid}'
        add_log(logMsg)
        time.sleep(3)
        dev_config_topic = f'/devices/{ID}/config'
        subs_id = self.client.subscribe(dev_config_topic,1)
        self.client.message_callback_add(dev_config_topic,self.on_config_msg)
        add_log('GCP subscription request sent for topic ' + dev_config_topic + ' ID ' + str(subs_id[1]))

    def publish_state(self,num,state):
        if num in attachedDev:
            state_topic = f'/devices/{attachedDev[num]}/state'
            res = self.client.publish(state_topic,state,1)
            logMsg = f'Publishing to GCP (ID {res.mid}) topic {state_topic}: \n' + str(state)
            add_log(logMsg)    
        else:
            logMsg = f'Received state is from unknown device\n' + state
            add_log(logMsg)

    def on_connect(self, unused_client, unused_userdata, unused_flags, rc):
        # Function when device connected
        logMsg = 'Connected to GCP MQTT: \n' + error_str(rc) 
        self.isConnect = True
        add_log(logMsg)
    
    def on_disconnect(self, unused_client, unused_userdata, rc):
        # Function when device disconnected
        global attachedDev
        self.isConnect = False
        logMsg = 'Disconnected from GCP MQTT: \n' + error_str(rc)
        add_log(logMsg)
        self.connect()
        for key,val in zip(attachedDev.keys(),attachedDev.values()):
            keyName = f'{key}_rsa_private.pem'
            self.req_attachment(val,dev_keyDir+keyName)

    def on_publish(self, unused_client, unused_userdata, mid):
        # Function when receive PUBACK
        logMsg = f'Publish to GCP (ID {mid}) successful'
        add_log(logMsg)

    def on_subscribe(self,client, unused_userdata, mid, granted_qos):
         # Function when subscription request responded
        add_log('Respond for GCP subscription request ID ' + str(mid) + '\nQoS ' + str(granted_qos[0]))       

    def on_config_msg(self, unused_client, unused_userdata, message):
        # Function to handle config message from GCP
        global sampling_freq
        dev_config = message.topic.split('/')[2]
        logMsg = f'Received config message on GCP topic {message.topic}\n{message.payload}'
        for key,val in zip(attachedDev.keys(),attachedDev.values()):
            if val == dev_config:
                if key == gw_DEVID:
                    cfg = json.loads(message.payload.decode('utf-8'))
                    if 'sampling' in cfg:
                        sampling_freq = cfg['sampling']
                        logMsg = logMsg + f'\nDEV001 Sampling changed to {sampling_freq}'
                        state = {
                            'devID':key,
                            'sampling':sampling_freq
                        }
                        self.publish_state(key,json.dumps(state))
                else:
                    self.local_handler.publish_config(key,message.payload.decode('utf-8'))
                    logMsg = logMsg + f'\nConfig found for {key}'
        add_log(logMsg)

    def on_unknown_msg(self, unused_client, unused_userdata, message):
        # Function when a new publish occured in unknown topic
        logMsg = "An unknown message from GCP topic " + str(message.topic) + "\n"
        logMsg = logMsg + str(message.payload)
        add_log(logMsg)

    def stop(self):
        add_log('Stopping GCP client')
        self.client.disconnect()
        self.client.loop_stop()

### Handle connection to local MQTT
class mqtt_local():
    def __init__(self):
        self.cloud_handler = None
        self.isConnect = False
        # Set MQTT Client
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_message = self.on_unknown_msg
        self.client.on_subscribe = self.on_subscribe
        self.client.message_callback_add(local_data_topic,self.on_gw1_pub_msg)
        self.client.message_callback_add(local_state_topic,self.on_state_msg)
        add_log('Connection to Local MQTT Initiated')

    def connect(self):
        # Connect to GCP
        self.client.connect(local_hostname,local_port)
        add_log('Trying to connect to Local MQTT')
        self.client.loop_start()
        subs_id = self.client.subscribe(local_data_topic,1)
        add_log('Local subscription request sent for topic ' + local_data_topic + ' ID ' + str(subs_id[1]))
        subs_id = self.client.subscribe(local_state_topic,1)
        add_log('Local subscription request sent for topic ' + local_state_topic + ' ID ' + str(subs_id[1]))
        self.wait_connect()

    def wait_connect(self,timeout = 10):
        total_time = 0
        while not self.isConnect and total_time < timeout:
            time.sleep(1)
            total_time += 1
        if not self.isConnect:
            logMsg = 'Cannot connect to Local MQTT' 
            add_log(logMsg)
            return False
        else:
            return True

    def publish_config(self,devid,msg):
        # Function to send device config
        config_topic = f'{devid}/config'
        res = self.client.publish(config_topic,msg,1)
        logMsg = f'Publishing to local network (ID {res.mid}) : \n' + str(msg)
        add_log(logMsg)

    def on_connect(self, unused_client, unused_userdata, unused_flags, rc):
        # Function when device connected
        logMsg = 'Connected to Local MQTT: \n' + error_str(rc) 
        self.isConnect = True
        add_log(logMsg)
    
    def on_subscribe(self,client, unused_userdata, mid, granted_qos):
        # Function when subscription request responded
        add_log('Respond for local MQTT subscription request ID ' + str(mid) + '\nQoS ' + str(granted_qos[0]))

    def on_disconnect(self, unused_client, unused_userdata, rc):
        # Function when device disconnected
        self.isConnect = False
        logMsg = 'Disconnected from Local MQTT: \n' + error_str(rc)
        add_log(logMsg)

    def on_publish(self, unused_client, unused_userdata, mid):
        # Function when receive PUBACK
        logMsg = f'Publish to local network (ID {mid}) successful'
        add_log(logMsg)

    def on_gw1_pub_msg(self, unused_client, unused_userdata, message):
        # Function when a new publish occured in /gw1/pub
        logMsg = "A new publish on local topic " + str(message.topic) + "\n"
        msg = str(message.payload.decode('utf-8')).replace('\r\n','')
        logMsg = logMsg + str(message.payload)
        add_log(logMsg)
        self.cloud_handler.send_data(msg)

    def on_state_msg(self, unused_client, unused_userdata, message):
        state = message.payload.decode('utf-8')
        statejson = json.loads(state)
        if 'devID' in statejson:
            logMsg = f'Received state from local MQTT\n{message.payload}'
            add_log(logMsg)
            self.cloud_handler.publish_state(statejson['devID'],state)
        else:
            logMsg = f'Received state without identity\n' + message.payload

    def on_unknown_msg(self, unused_client, unused_userdata, message):
        # Function when a new publish occured in unknown topic
        logMsg = "An unknown message from local topic " + str(message.topic) + "\n"
        logMsg = logMsg + str(message.payload)
        add_log(logMsg)

    def stop(self):
        add_log('Stopping Local MQTT client')
        self.client.disconnect()
        self.client.loop_stop()

### Main function
def main():
    gcp = mqtt_gcp()
    loc = mqtt_local()
    gcp.local_handler = loc
    loc.cloud_handler = gcp
    ieq = ieq_sim()

    try:
        gcp.connect()
        loc.connect()
        while True:
            data = ieq.gen_json()
            gcp.send_data(data)
            time.sleep(sampling_freq)
    
    except Exception as er:
        add_log('Program terminated')
        add_log(er)

    finally:
        gcp.stop()
        loc.stop()

if __name__ == '__main__':
    main()