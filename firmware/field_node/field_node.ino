#include <DallasTemperature.h>
#include <OneWire.h>
#include "secrets.h"
#include <WiFi.h>
#include <ModbusIP_ESP8266.h>

ModbusIP mb;
uint16_t heartbeatCounter = 0;

const uint8_t ONE_WIRE_PIN=D2;
OneWire wired(ONE_WIRE_PIN);
DallasTemperature sensors(&wired);
float tempC;
unsigned long lastTimeTemp=0;

unsigned long lastTimeWifi=0;

unsigned long lastTimeVolt=0;
const int SAMPLES=16;

bool q1ClosedState=false;

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
  WiFi.begin(WIFI_SSID, WIFI_PASS);

  mb.server();

  bool iregOK=mb.addIreg(0,0,4);
  bool istsOK=mb.addIsts(0,0,7);
  bool coilOK=mb.addCoil(0,0,4);
  bool hregOK=mb.addHreg(0,0,2);

  if(!iregOK | !istsOK | !coilOK | !hregOK){
    Serial.println("WARNING: Modbus I/O Map configuration failed!");
  }

  pinMode(D9, OUTPUT);

  sensors.begin();
  sensors.setWaitForConversion(false);
  sensors.requestTemperatures();

  analogSetPinAttenuation(A0, ADC_11db);
  analogSetPinAttenuation(A1, ADC_11db);
}

void loop() {
  mb.task();

  if(mb.Coil(0)==1){
    q1ClosedState=true;
    mb.Coil(0,0);
  }
  
  if(mb.Coil(1)==1){
    q1ClosedState=false;
    mb.Coil(1,0);
  }

  mb.Ists(0, q1ClosedState);
  mb.Ists(1, !q1ClosedState);

  digitalWrite(D9, q1ClosedState);

  unsigned long now=millis();

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
