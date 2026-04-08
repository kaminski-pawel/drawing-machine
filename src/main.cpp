#include <Arduino.h>
#define onboardLED 13

void setup()
{
  pinMode(onboardLED, OUTPUT);
}

void loop()
{
  digitalWrite(onboardLED, HIGH);
  delay(500);
  digitalWrite(onboardLED, LOW);
  delay(500);
}
