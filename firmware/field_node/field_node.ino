#include <DallasTemperature.h>
#include <OneWire.h>

const uint8_t ONE_WIRE_PIN=D2;
OneWire wired(ONE_WIRE_PIN);
DallasTemperature sensors(&wired);
float tempC;
unsigned long lastTimeTemp=0;

unsigned long lastTimeVolt=0;
const int SAMPLES=16;

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

  sensors.begin();
  sensors.setWaitForConversion(false);
  sensors.requestTemperatures();

  analogSetPinAttenuation(A0, ADC_11db);
  analogSetPinAttenuation(A1, ADC_11db);
}

void loop() {
  unsigned long now=millis();

  if (now-lastTimeVolt>=500) {
    lastTimeVolt=now;

    uint32_t avgMainMv=readGaugeMv(A0);
    uint32_t avgBackupMv=readGaugeMv(A1);

    Serial.printf("Average U_MAIN=%lumV\n", avgMainMv);
    Serial.printf("Average U_BACKUP=%lumV\n", avgBackupMv);
  }

  if(now-lastTimeTemp>=1000){
    lastTimeTemp=now;

    tempC=sensors.getTempCByIndex(0);

    Serial.printf("Temperature = %.1f°C\n", tempC);

    sensors.requestTemperatures();
  }
}
