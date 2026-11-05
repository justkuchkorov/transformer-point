unsigned long lasttime=0;
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
  analogSetPinAttenuation(A0, ADC_11db);
  analogSetPinAttenuation(A1, ADC_11db);
}

void loop() {
  unsigned long now=millis();
  if (now-lasttime>=500) {
    lasttime=now;
    uint32_t avgMainMv=readGaugeMv(A0);
    uint32_t avgBackupMv=readGaugeMv(A1);

    Serial.printf("Average U_MAIN=%lumV\n", avgMainMv);
    Serial.printf("Average U_BACKUP=%lumV\n", avgBackupMv);
  }
}
