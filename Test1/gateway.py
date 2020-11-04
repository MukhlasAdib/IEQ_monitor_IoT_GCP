import datetime
import json
import os
import ssl
import time
import jwt
import paho.mqtt.client as mqtt


### Common Variables
jwt_alg = 'RS256'
ca_certs = 'roots.pem'

### Variables for GCP connection
gw_private = 'rsa_private.pem'
project_id = 'tactical-patrol-276605'
gcp_region = 'asia-east1'
gcp_hostname = 'mqtt.googleapis.com'
gcp_port = 8883
gw_registyID = 'tugas_scada_tim7_testReg'
gw_deviceID = 'tugas_scada_tim7_testDev1'
pub_gcp_topic = f'/devices/{gw_deviceID}/events'

### Common functions
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

### IEQ Data generator
class ieq_sim():
    def gen_data(self):
        #Generate simulated data
        print('Under construction')

    def gen_json(self):
        # Generate json formatted data
        print('Under construction')

### Handle connection to GCP MQTT
class gateway_gcp():
    def __init__(self):
        self.isConnect_gcp = False
        self.logList = []
        self.maxLog = 50
        # Set MQTT Client
        self.client = mqtt.Client(client_id = f'projects/{project_id}/locations/{gcp_region}/registries/{gw_registyID}/devices/{gw_deviceID}')
        self.client.username_pw_set(
            username = 'unused',
            password = create_jwt(project_id,gw_private,jwt_alg))
        self.client.tls_set(ca_certs=ca_certs, tls_version=ssl.PROTOCOL_TLSv1_2)
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_publish = self.on_publish
        self.add_log('Initiated')

    def connect(self):
        # Connect to GCP
        self.client.connect(gcp_hostname,gcp_port)
        self.add_log('Trying to connect to GCP')
        self.client.loop_start()
        return self.wait_connect_gcp()

    def wait_connect_gcp(self,timeout = 10):
        total_time = 0
        while not self.isConnect_gcp and total_time < timeout:
            time.sleep(1)
            total_time += 1
        if not self.isConnect_gcp:
            logMsg = 'Cannot connect to GCP MQTT' 
            self.add_log(logMsg)
            return False
        else:
            return True

    def send_data(self,data):
        # Send data to GCP handle
        res = self.client.publish(pub_gcp_topic, data, qos=1)
        logMsg = f'Publishing (ID {res.mid}) : \n' + str(data)
        self.add_log(logMsg)
        res.wait_for_publish()

    def on_connect(self, unused_client, unused_userdata, unused_flags, rc):
        # Function when device connected
        logMsg = 'Connected to GCP MQTT: \n' + error_str(rc) 
        self.isConnect_gcp = True
        self.add_log(logMsg)
    
    def on_disconnect(self, unused_client, unused_userdata, rc):
        # Function when device disconnected
        self.isConnect_gcp = False
        logMsg = 'Disconnected from GCP MQTT: \n' + error_str(rc)
        self.add_log(logMsg)

    def on_publish(self, unused_client, unused_userdata, mid):
        # Function when receive PUBACK
        logMsg = f'Publish (ID {mid}) successful'
        self.add_log(logMsg)

    def add_log(self, msg):
        # Add log history
        now = datetime.datetime.now()
        date_time = now.strftime("%d-%m-%Y, %H:%M:%S")
        logStr = date_time + '\n'
        logStr = logStr + msg
        print(logStr + '\n')
        self.logList.append(logStr)
        if len(self.logList) > self.maxLog:
            self.logList.pop(0)

    def stop(self):
        self.add_log('Stopping GCP client')
        self.client.disconnect()
        self.client.loop_stop()

def main():
    gcp = gateway_gcp()
    gcp.connect()
    
    i = 0
    while i <= 20:
        gcp.send_data('test' + str(i))
        i = i + 1
        time.sleep(2)
    
    gcp.stop()

if __name__ == '__main__':
    main()