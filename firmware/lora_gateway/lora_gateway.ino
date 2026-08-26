#include "../common/config.h"
unsigned long lastSequence[4]={0,0,0,0};
void setup(){Serial.begin(115200);/* initialize LoRa, Wi-Fi/MQTT independently */}
void loop(){/* receive without blocking; validate CRC/JSON/node; discard sequence <= lastSequence; queue HTTP/MQTT retry */}
