import datetime
import json
import os
import ssl
import time
import jwt
import paho.mqtt.client as mqtt
import json

### Common Variables
jwt_alg = 'RS256'
ca_certs = 'roots.pem'
fdate = ''
num = 1
fname = ''

### Variables for GCP connection
gw_private = 'rsa_private.pem'
project_id = 'tactical-patrol-276605'
gcp_region = 'asia-east1'
gcp_hostname = 'mqtt.googleapis.com'
gcp_port = 8883
gw_registyID = 'tugas_scada_tim7_testReg'
gw_deviceID = 'tugas_scada_tim7_testDev1'
pub_gcp_topic = f'/devices/{gw_deviceID}/events'

### Variables for Local Connection
local_hostname = '192.168.100.6'
local_port = 1883
data_topic = 'gw1/pub'

### Common functions
def renew_filename():
    # Create new filename for logging
    global fdate
    global num
    global fname
    now = datetime.datetime.now()
    fdate = now.strftime("%Y%m%d")
    num = 1
    for file in os.listdir():
        if file.endswith('_test1_log.txt') and file.startswith(fdate):
            fnum = file.split('_')[1]
            num = int(fnum) + 1
    fname = fdate + '_' + str(num) + '_test1_log.txt'
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
    logStr = logStr + msg + '\n'
    print(logStr)
    fdate_new = now.strftime("%Y%m%d")
    if fdate_new != fdate:
        renew_filename()
    with open(fname, "a") as f:
        f.write(logStr + '\n')

### IEQ Data generator
class ieq_sim():
    def __init__(self):
        self.temp_sim = {'min':0,'max':100,'delta':10}
        self.rh_sim = {'min':0,'max':100,'delta':10}
        self.lux_sim = {'min':0,'max':100,'delta':10}
        self.co2_sim = {'min':0,'max':100,'delta':10}
        self.spl_sim = {'min':0,'max':100,'delta':10}
        self.temp = self.temp_sim['min']
        self.rh = self.rh_sim['min']
        self.lux = self.lux_sim['min']
        self.co2 = self.co2_sim['min']
        self.spl = self.spl_sim['min']

    def progress(self,param,sim):
        # Calculate the new IEQ parameter
        param = param + sim['delta']
        if param > sim['max']: param = sim['min']
        return param

    def update(self):
        # Update all of IEQ parameters
        self.temp = self.progress(self.temp,self.temp_sim)
        self.rh = self.progress(self.rh,self.rh_sim)
        self.lux = self.progress(self.lux,self.lux_sim)
        self.co2 = self.progress(self.co2,self.co2_sim)
        self.spl = self.progress(self.spl,self.spl_sim)

    def gen_json(self):
        now = datetime.datetime.now()
        nowDate = now.strftime("%Y-%m-%d")
        nowTime = now.strftime("%H:%M:%S")
        ieq_dict = {
            'temp': self.temp,
            'rh': self.rh,
            'lux': self.lux,
            'co2': self.co2,
            'spl': self.spl,
            'date': nowDate,
            'time': nowTime,
            'devID': 'DEV001',
            'gwyID': 'GWY001' 
        }
        jsonStr = json.dumps(ieq_dict)
        self.update()
        return jsonStr

### Handle connection to GCP MQTT
class mqtt_gcp():
    def __init__(self):
        self.isConnect = False
        # Set MQTT Client
        self.client = mqtt.Client(client_id = f'projects/{project_id}/locations/{gcp_region}/registries/{gw_registyID}/devices/{gw_deviceID}')
        self.client.username_pw_set(
            username = 'unused',
            password = create_jwt(project_id,gw_private,jwt_alg))
        self.client.tls_set(ca_certs=ca_certs, tls_version=ssl.PROTOCOL_TLSv1_2)
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_publish = self.on_publish
        add_log('Connection to GCP Initiated')

    def connect(self):
        # Connect to GCP
        self.client.connect(gcp_hostname,gcp_port)
        add_log('Trying to connect to GCP')
        self.client.loop_start()
        self.wait_connect()

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
        while not self.isConnect: self.connect()
        res = self.client.publish(pub_gcp_topic, data, qos=1)
        logMsg = f'Publishing to GCP (ID {res.mid}) : \n' + str(data)
        add_log(logMsg)

    def on_connect(self, unused_client, unused_userdata, unused_flags, rc):
        # Function when device connected
        logMsg = 'Connected to GCP MQTT: \n' + error_str(rc) 
        self.isConnect = True
        add_log(logMsg)
    
    def on_disconnect(self, unused_client, unused_userdata, rc):
        # Function when device disconnected
        self.isConnect = False
        logMsg = 'Disconnected from GCP MQTT: \n' + error_str(rc)
        add_log(logMsg)

    def on_publish(self, unused_client, unused_userdata, mid):
        # Function when receive PUBACK
        logMsg = f'Publish ro GCP (ID {mid}) successful'
        add_log(logMsg)

    def stop(self):
        add_log('Stopping GCP client')
        self.client.disconnect()
        self.client.loop_stop()

### Handle connection to local MQTT
class mqtt_local():
    def __init__(self):
        self.isConnect = False
        # Set MQTT Client
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_message = self.on_gw1_pub_msg
        self.client.on_subscribe = self.on_subscribe
        self.client.message_callback_add(data_topic,self.on_gw1_pub_msg)
        add_log('Connection to Local MQTT Initiated')

    def connect(self):
        # Connect to GCP
        self.client.connect(local_hostname,local_port)
        add_log('Trying to connect to Local MQTT')
        self.client.loop_start()
        subs_id = self.client.subscribe(data_topic,1)
        add_log('Subscription request sent for topic ' + data_topic + ' ID ' + str(subs_id[1]))
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

    def on_connect(self, unused_client, unused_userdata, unused_flags, rc):
        # Function when device connected
        logMsg = 'Connected to Local MQTT: \n' + error_str(rc) 
        self.isConnect = True
        add_log(logMsg)
    
    def on_subscribe(self,client, unused_userdata, mid, granted_qos):
        # Function when subscription request responded
        add_log('Respond for subscription request ID ' + str(mid) + '\n QoS ' + str(granted_qos[0]))

    def on_disconnect(self, unused_client, unused_userdata, rc):
        # Function when device disconnected
        self.isConnect = False
        logMsg = 'Disconnected from Local MQTT: \n' + error_str(rc)
        add_log(logMsg)

    def on_gw1_pub_msg(self, unused_client, unused_userdata, message):
        # Function when a new publish occured in /gw1/pub
        logMsg = "A new publish on local topic " + str(message.topic) + "\n"
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
    ieq = ieq_sim()
    try:
        gcp.connect()
        loc.connect()
        while True:
            data = ieq.gen_json()
            gcp.send_data(data)
            time.sleep(5)
    
    except:
        add_log('Program terminated')

    finally:
        gcp.stop()
        loc.stop()

if __name__ == '__main__':
    main()