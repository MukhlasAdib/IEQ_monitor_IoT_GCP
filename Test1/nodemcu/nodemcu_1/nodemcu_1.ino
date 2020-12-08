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
#include <ArduinoJson.h>
#include "genData.h"

void startCon();
void mqttCon(int maxTry);
void callback(char* topic, byte* payload, unsigned int length);
void publishState(int sampling);
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
DynamicJsonDocument jsonData(1024);

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
    Serial.println();
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

void callback(char* topic, byte* payload, unsigned int length){
  Serial.println();
  Serial.println("----New Message----");
  Serial.print("channel:");
  Serial.println(topic);
  Serial.print("data:");
  Serial.write(payload,length);
  Serial.println();

  DeserializationError jsonError = deserializeJson(jsonData, payload);
  if (jsonError){
    Serial.print(F("Failed to deserialize JSON: "));
    Serial.println(jsonError.f_str());
  } else if(jsonData["devID"]!=mqttID){
    Serial.print("Received wrong config: ");
    const char* msgID = jsonData["devID"];
    Serial.println(msgID);
  } else if(!jsonData.containsKey("sampling")){
    Serial.println("No sampling information");   
  } else{
    f_sampling = int(jsonData["sampling"]);
    f_sampling = f_sampling * 1000;
    if (f_sampling < 1000){
      f_sampling = 1000;
    }
    publishTask.setInterval(f_sampling);
    Serial.print("Sampling interval changed to (ms) ");
    Serial.println(f_sampling);
  }
  publishState(f_sampling/1000);
}

void publishState(int sampling){
  String msg = "{\"devID\":\"" + mqttID + "\",";
  msg += "\"sampling\":" + String(sampling) + "}";
  int str_len = msg.length()+1;
  char postDataChar[str_len];
  msg.toCharArray(postDataChar,str_len);
  Serial.println();
  if (WiFi.status() == WL_CONNECTED){
    mqttCon(5);
    client.publish(TOPIC_STATE,postDataChar);
    Serial.print("Sending to topic ");
    Serial.println(TOPIC_STATE);
    Serial.println(msg);
  } else{
    Serial.println("Cannot connect to AP");
  }
}

void publishData(){
  nowTime = millis()/1000;
  postData = formatData(nowTime, mqttID);
  int str_len = postData.length()+1;
  char postDataChar[str_len];
  postData.toCharArray(postDataChar,str_len);
  Serial.println();
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
