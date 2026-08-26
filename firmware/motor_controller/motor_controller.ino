#include "../common/config.h"
bool armed=false; long positionSteps=0; unsigned long motionStarted=0;
void disableMotor(){digitalWrite(PIN_ENABLE,HIGH);armed=false;}
void setup(){pinMode(PIN_ENABLE,OUTPUT);pinMode(PIN_STEP,OUTPUT);pinMode(PIN_DIR,OUTPUT);pinMode(PIN_ESTOP,INPUT_PULLUP);pinMode(PIN_LIMIT_TOP,INPUT_PULLUP);pinMode(PIN_LIMIT_BOTTOM,INPUT_PULLUP);disableMotor();}
void loop(){if(!digitalRead(PIN_ESTOP)||!digitalRead(PIN_LIMIT_TOP)||!digitalRead(PIN_LIMIT_BOTTOM)||(armed&&millis()-motionStarted>MOTOR_TIMEOUT_MS)||positionSteps<0||positionSteps>MAX_TRAVEL_STEPS)disableMotor();/* Commands must explicitly arm; motion uses millis/micros scheduling, never delay(). */}
