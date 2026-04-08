#include <Arduino.h>
#include <AFMotor.h>
#include <Servo.h>

// NEMA 17 on Port 2 (M3 and M4)
AF_Stepper motor(200, 2);
Servo servo1;

void setup()
{
  Serial.begin(9600);
  Serial.println("System Starting...");

  // Servo 1 header is Pin 10 on V1 shield
  servo1.attach(10);

  // Start slow to ensure the L293D doesn't trip
  motor.setSpeed(10);
}

void loop()
{
  // --- Motor Move ---
  Serial.println("Motor Moving...");
  motor.step(100, FORWARD, DOUBLE); // Use DOUBLE for more torque
  delay(500);
  motor.step(100, BACKWARD, DOUBLE);

  // RELEASE motor so it doesn't bake the chips while servo moves
  motor.release();
  delay(500);

  // --- Servo Move ---
  Serial.println("Servo Moving...");
  for (int angle = 0; angle <= 180; angle += 5)
  {
    servo1.write(angle);
    delay(30);
  }
  for (int angle = 180; angle >= 0; angle -= 5)
  {
    servo1.write(angle);
    delay(30);
  }

  delay(200);
}
