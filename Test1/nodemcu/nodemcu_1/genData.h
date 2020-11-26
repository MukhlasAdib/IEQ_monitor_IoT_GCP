//Program ini dibuat untuk menghasilkan data IEQ dengan pola tertentu
//Algoritmanya yaitu tiap variabel ditambahkan dnegan nilai yang konstan
//Perhitungan dimulai dari nilai min ketika dihidupkan
//Jika nilai sudah mencapai max, maka nilai kembali ke min
//Suhu: min 20 max 30
//RH: min 40 max 80
//Iluminansi: min 200 max 500
//Lmax dan Ltot: min 10 max 70
//CO2: min 100 max 1500
//Membuat format json dari input data

float calcIEQ(int timeSec, float minVal, float maxVal, float noiseFactor);
String formatData(int nowTime, String devID);

float f = 2 * 3.14 * 1/86400; 
float temp_minVal = 23;
float temp_maxVal = 30;
float temp_noise = 0.01;
float rh_minVal = 50;
float rh_maxVal = 80;
float rh_noise = 0.025;
float lux_minVal = 200;
float lux_maxVal = 300;
float lux_noise = 0.05;
float co2_minVal = 250;
float co2_maxVal = 500;
float co2_noise = 0.1;
float spl_minVal = 25;
float spl_maxVal = 45;
float spl_noise = 0.05;

float calcIEQ(int timeSec, float minVal, float maxVal, float noiseFactor){
  float val;
  float noise = random(-100,100)*(noiseFactor*maxVal)/100;
  val = (maxVal+minVal)/2 - cos(f*timeSec)*(maxVal-minVal)/2;
  val = val + noise;
  return val;
}

String formatData(int nowTime, String devID){
  float temp = calcIEQ(nowTime, temp_minVal, temp_maxVal, temp_noise);
  float rh = calcIEQ(nowTime, rh_minVal, rh_maxVal, rh_noise);
  float lux = calcIEQ(nowTime, lux_minVal, lux_maxVal, lux_noise);
  float spl = calcIEQ(nowTime, spl_minVal, spl_maxVal, spl_noise);
  float co2 = calcIEQ(nowTime, co2_minVal, co2_maxVal, co2_noise);
  
  String postData = "{\"devID\":\"" + devID;
  postData += "\", \"temp\":" + String(temp);
  postData += ", \"rh\":" + String(rh);
  postData += ", \"lux\":" + String(lux);
  postData += ", \"spl\":" + String(spl);
  postData += ", \"co2\":" + String(co2) + "}";

  return postData;
}
