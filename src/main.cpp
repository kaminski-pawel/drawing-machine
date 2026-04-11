#include <Arduino.h>
#include <AFMotor.h>
#include <Servo.h>

namespace
{
  constexpr uint16_t kStepsPerRevolution = 200;
  constexpr uint16_t kStepperTestSteps = 24;
  constexpr uint8_t kStepperRpm = 8;
  constexpr uint8_t kServoPin = 10;
  constexpr uint16_t kServoCenterUs = 1500;
  constexpr uint16_t kServoLeftUs = 1200;
  constexpr uint16_t kServoRightUs = 1800;
  constexpr uint16_t kPauseMs = 500;

  AF_Stepper leftMotor(kStepsPerRevolution, 1);
  AF_Stepper rightMotor(kStepsPerRevolution, 2);
  Servo penServo;

  void releaseAllMotors()
  {
    leftMotor.release();
    rightMotor.release();
  }

  void stepMotor(const __FlashStringHelper *label,
                 AF_Stepper &motor,
                 uint16_t steps,
                 uint8_t direction)
  {
    Serial.print(label);
    Serial.println(direction == FORWARD ? F(" forward") : F(" backward"));
    motor.step(steps, direction, SINGLE);
    motor.release();
    delay(kPauseMs);
  }

  void stepBoth(uint16_t steps, uint8_t leftDirection, uint8_t rightDirection)
  {
    Serial.println(F("Both steppers moving together"));

    for (uint16_t stepIndex = 0; stepIndex < steps; ++stepIndex)
    {
      leftMotor.onestep(leftDirection, SINGLE);
      rightMotor.onestep(rightDirection, SINGLE);
      delay(15);
    }

    releaseAllMotors();
    delay(kPauseMs);
  }

  void moveServo(uint16_t pulseWidthUs, const __FlashStringHelper *label)
  {
    Serial.print(F("Servo -> "));
    Serial.println(label);
    penServo.writeMicroseconds(pulseWidthUs);
    delay(700);
  }
}

void setup()
{
  Serial.begin(115200);
  Serial.println(F("Vertical plotter connection test"));
  Serial.println(F("Keep the carriage unloaded and be ready to cut power if a motor overheats."));

  penServo.attach(kServoPin);
  penServo.writeMicroseconds(kServoCenterUs);
  delay(500);

  leftMotor.setSpeed(kStepperRpm);
  rightMotor.setSpeed(kStepperRpm);
  releaseAllMotors();

  Serial.println(F("Test starts in 2 seconds..."));
  delay(2000);
}

void loop()
{
  Serial.println(F("--- New test pass ---"));

  moveServo(kServoCenterUs, F("center"));
  moveServo(kServoLeftUs, F("pen up test"));
  moveServo(kServoRightUs, F("pen down test"));
  moveServo(kServoCenterUs, F("center"));

  stepMotor(F("Left stepper"), leftMotor, kStepperTestSteps, FORWARD);
  stepMotor(F("Left stepper"), leftMotor, kStepperTestSteps, BACKWARD);

  stepMotor(F("Right stepper"), rightMotor, kStepperTestSteps, FORWARD);
  stepMotor(F("Right stepper"), rightMotor, kStepperTestSteps, BACKWARD);

  stepBoth(kStepperTestSteps, FORWARD, FORWARD);
  stepBoth(kStepperTestSteps, BACKWARD, BACKWARD);

  Serial.println(F("Waiting 2 seconds before repeating."));
  delay(2000);
}
