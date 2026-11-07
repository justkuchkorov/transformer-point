#include <DallasTemperature.h>
#include <OneWire.h>
#include "secrets.h"
#include <WiFi.h>
#include <ModbusIP_ESP8266.h>

ModbusIP mb;
uint16_t heartbeatCounter = 0;

IPAddress localIp(192, 168, 100, 48);
IPAddress gatewayIp(192, 168, 100, 1);
IPAddress subnetMask(255, 255, 255, 0);

const uint8_t ONE_WIRE_PIN=D2;
OneWire wired(ONE_WIRE_PIN);
DallasTemperature sensors(&wired);
float tempC;
unsigned long lastTimeTemp=0;

unsigned long lastTimeWifi=0;

unsigned long lastTimeVolt=0;
const int SAMPLES=16;

enum BreakerState{BRK_OPEN, BRK_CLOSING, BRK_CLOSED};
BreakerState q1State=BRK_OPEN;
unsigned long q1CloseStart=0;

BreakerState q2State=BRK_OPEN;
unsigned long q2CloseStart=0;
unsigned long lastTimeLamp=0;

bool q1Stuck=false;
bool q2Stuck=false;

uint32_t readGaugeMv(uint8_t pin){
  uint32_t sumbox=0;
  for(int i=1;i<=SAMPLES;i++){
    sumbox+=analogReadMilliVolts(pin);
  }
  return sumbox/SAMPLES;
}

void setup() {
  Serial.begin(115200);
  Serial.println("field_node start");

  WiFi.mode(WIFI_STA);
  bool IpOK = WiFi.config(localIp, gatewayIp, subnetMask);
  WiFi.begin(WIFI_SSID, WIFI_PASS);

  if(!IpOK){
    Serial.println("WARNING: IP failed!");
  }
   
  mb.server();

  bool iregOK=mb.addIreg(0,0,4);
  bool istsOK=mb.addIsts(0,0,7);
  bool coilOK=mb.addCoil(0,0,4);
  bool hregOK=mb.addHreg(0,1500,2);

  if(!iregOK | !istsOK | !coilOK | !hregOK){
    Serial.println("WARNING: Modbus I/O Map configuration failed!");
  }

  pinMode(D9, OUTPUT);
  pinMode(D3, INPUT_PULLUP);
  pinMode(D12, INPUT_PULLUP);

  sensors.begin();
  sensors.setWaitForConversion(false);
  sensors.requestTemperatures();

  analogSetPinAttenuation(A0, ADC_11db);
  analogSetPinAttenuation(A1, ADC_11db);
}

void loop() {
  mb.task();

  unsigned long now=millis();

  if(digitalRead(D3)==LOW){
    q1Stuck=true;
    mb.Ists(5,1);
  }
  else{
    q1Stuck=false;
    mb.Ists(5,0);
  }

  if(digitalRead(D12)==LOW){
    q2Stuck=true;
    mb.Ists(6,1);
  }
  else{
    q2Stuck=false;
    mb.Ists(6,0);
  }

  if(mb.Coil(0)==1){
    if(q1State==BRK_OPEN && q2State==BRK_OPEN && q1Stuck==false){
      q1State=BRK_CLOSING;
      q1CloseStart=now;
    }
    else {
        Serial.println("Q1 CLOSE refused");
    }
    mb.Coil(0,0);
  }
  
  if(q1State==BRK_CLOSING && now-q1CloseStart>=mb.Hreg(0) && q1Stuck==false){
    q1State=BRK_CLOSED;
  }

  if(mb.Coil(1)==1){
    if(q1Stuck==false){
      q1State=BRK_OPEN;
    }
    else{
      Serial.println("Q1 OPEN refused");
    }  
    mb.Coil(1,0);
  }

  if(mb.Coil(2)==1){
    if(q2State==BRK_OPEN && q1State==BRK_OPEN && q2Stuck==false){
      q2State=BRK_CLOSING;
      q2CloseStart=now;
    }
    else {
        Serial.println("Q2 CLOSE refused");
    }
    mb.Coil(2,0);
  }
  
  if(q2State==BRK_CLOSING && now-q2CloseStart>=mb.Hreg(1) && q2Stuck==false){
    q2State=BRK_CLOSED;
  }

  if(mb.Coil(3)==1){
    if(q2Stuck==false){
      q2State=BRK_OPEN;
    }
    else{
      Serial.println("Q2 OPEN refused");
    }  
    mb.Coil(3,0);
  }

  if (q1State==BRK_CLOSED) {
    mb.Ists(0,1);
    mb.Ists(1,0);
    digitalWrite(D9, 1);
  }
  else if (q1State==BRK_OPEN) {
    mb.Ists(1,1);
    mb.Ists(0,0);
    digitalWrite(D9, 0);
  }
  else {
      mb.Ists(0,0);
      mb.Ists(1,0);
      digitalWrite(D9, 0);
  }

  if (q2State==BRK_CLOSED) {
    mb.Ists(2,1);
    mb.Ists(3,0);
  }
  else if (q2State==BRK_OPEN) { 
    mb.Ists(3,1);
    mb.Ists(2,0);
  }
  else {
      mb.Ists(2,0);
      mb.Ists(3,0);
  }

  if(now-lastTimeLamp>=100){
    lastTimeLamp=now;
    if(q2State==BRK_CLOSED){
      rgbLedWrite(D8, 30, 0, 0);
    }
    else{
    rgbLedWrite(D8, 0, 0, 0);
    }
  }
  

  if (now-lastTimeVolt>=500) {
    lastTimeVolt=now;

    uint32_t avgMainMv=readGaugeMv(A0);
    uint32_t avgBackupMv=readGaugeMv(A1);

    Serial.printf("Average U_MAIN=%lumV\n", avgMainMv);
    Serial.printf("Average U_BACKUP=%lumV\n", avgBackupMv);

    mb.Ireg(0, (uint16_t)avgMainMv);
    mb.Ireg(1, (uint16_t)avgBackupMv);
  }

  if(now-lastTimeTemp>=1000){
    lastTimeTemp=now;

    tempC=sensors.getTempCByIndex(0);

    Serial.printf("Temperature = %.1f°C\n", tempC);

    if(tempC!=DEVICE_DISCONNECTED_C){
      int16_t tempTenths = (int16_t)lroundf(tempC * 10.0f);

      mb.Ireg(2, (uint16_t)tempTenths);

      mb.Ists(4, 1);
    }
    else {
      mb.Ists(4, 0);
    }

    heartbeatCounter++;
    mb.Ireg(3, heartbeatCounter);

    sensors.requestTemperatures();
  }
  if(now-lastTimeWifi>=5000){
    lastTimeWifi=now;

    if(WiFi.status()==WL_CONNECTED){
      Serial.printf("WiFi: Connected! IP = %s | Signal = %d dBm\n", 
                    WiFi.localIP().toString().c_str(), 
                    WiFi.RSSI());
    }
    else {
      Serial.println("WiFi: connecting...");
    }
  }
}
