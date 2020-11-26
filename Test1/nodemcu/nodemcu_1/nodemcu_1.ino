//NodaA
//Upload IEQ data to User Server 
//Ganti ssid dan password pada /apconfig
//Task scheduler
//Parameters: Suhu, RH, Iluminansi, Lmax, Ltot, CO2
//Pengukuran Latensi
//Akses untuk cek status pada /
//include ota pada /update

#include <ESP8266WiFi.h>
#include <WiFiClient.h>
#include <PubSubClient.h>
#include <TaskScheduler.h>
#include "genData.h"

void startCon();
void mqttCon(int maxTry);
void callback(char* topic, byte* payload, unsigned int length){
  Serial.println("----New Message----");
  Serial.print("channel:");
  Serial.println(topic);
  Serial.print("data:");
  Serial.write(payload,length);
  Serial.println();
}
void uploadData();

const char* ssid = "SCADA_GWY001";
const char* password = "123sampai8";
String mqttID = "DEV002";
const char* mqtt_server = "192.168.200.1";
const int mqtt_port = 1883;
const char* TOPIC_DATA = "GWY/data";
const char* TOPIC_CONFIG = "DEV002/config";
const char* TOPIC_STATE = "GWY/state";

int f_sampling = 15000;
String postData;
int nowTime;

Task publishTask(f_sampling, TASK_FOREVER, &publishData);
Scheduler sendLoop;

WiFiClient wificlient;
PubSubClient client(wificlient);

void setup() {
  Serial.begin(9600);
  delay(10000);
  startCon();

  client.setServer(mqtt_server, mqtt_port);
  client.setCallback(callback);
  mqttCon(5);

  sendLoop.addTask(publishTask);
  publishTask.enable();
}

void loop() {
  sendLoop.execute();
  client.loop();
  if (WiFi.status() != WL_CONNECTED){
    startCon();
  }
}

void startCon(){
  Serial.println();
  Serial.println();
  Serial.print("Connecting to ");
  Serial.println(ssid);
  WiFi.begin(ssid, password);
  WiFi.mode(WIFI_STA);
  int i = 0;
  while (WiFi.status() != WL_CONNECTED && i<50) {
    delay(500);
    Serial.print(".");
    i++;
  }
  
  if (WiFi.status() == WL_CONNECTED){
    Serial.println();
    Serial.println("WiFi connected");
    Serial.print("IP address: ");
    Serial.println(WiFi.localIP());
    Serial.print("Gateway: ");
    Serial.println(WiFi.gatewayIP());
    Serial.print("SubnetMask: ");
    Serial.println(WiFi.subnetMask());
  }
  else {
    Serial.println("");
    Serial.println("Failed to connect to AP");
  }
}

void mqttCon(int maxTry){
  int i = 1;
  while (!client.connected() && i<=maxTry){
    Serial.println("Attempting MQTT connection...");
    if(client.connect(mqttID.c_str())){
      Serial.println("connected");
      delay(1000);
      client.subscribe(TOPIC_CONFIG);
    }else{
      Serial.println("Failed to connect");
      delay(5000); 
    }
    i = i + 1;
  }
}

void publishData(){
  nowTime = millis()/1000;
  postData = formatData(nowTime, mqttID);
  int str_len = postData.length()+1;
  char postDataChar[str_len];
  postData.toCharArray(postDataChar,str_len);
  if (WiFi.status() == WL_CONNECTED){
    mqttCon(5);
    client.publish(TOPIC_DATA,postDataChar);
    Serial.print("Sending to topic ");
    Serial.println(TOPIC_DATA);
    Serial.println(postDataChar);
  } else{
    Serial.println("Cannot connect to AP");
  }
}
