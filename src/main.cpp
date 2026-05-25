#include <Arduino.h>
#include <AFMotor.h>
#include <Servo.h>
#include <ctype.h>
#include <math.h>
#include <stdlib.h>
#include <string.h>

namespace
{
  constexpr uint16_t kStepsPerRevolution = 200;
  constexpr uint8_t kStepperRpm = 8;
  constexpr uint8_t kServoPin = 10;
  constexpr uint16_t kServoDefaultUs = 1500;
  constexpr uint16_t kServoMinUs = 600;
  constexpr uint16_t kServoMaxUs = 2400;
  constexpr uint16_t kServoSettleMs = 300;

  // Calibrate this for your pulley circumference (mm traveled for one motor revolution).
  constexpr float kMmPerRevolution = 40.0f;

  constexpr uint8_t kDefaultStepDelayMs = 10;
  constexpr uint8_t kMinStepDelayMs = 3;
  constexpr uint8_t kMaxStepDelayMs = 40;
  constexpr uint16_t kMaxMoveStepsPerMotor = 5000;

  constexpr size_t kCommandBufferLength = 96;

  AF_Stepper leftMotor(kStepsPerRevolution, 1);
  AF_Stepper rightMotor(kStepsPerRevolution, 2);
  Servo penServo;

  char commandBuffer[kCommandBufferLength];
  size_t commandLength = 0;

  int32_t currentLeftSteps = 0;
  int32_t currentRightSteps = 0;
  uint16_t currentServoUs = kServoDefaultUs;

  float stepsPerMm()
  {
    return static_cast<float>(kStepsPerRevolution) / kMmPerRevolution;
  }

  bool parseFloatToken(const char *token, char expectedPrefix, float &value)
  {
    if (token == nullptr || token[0] == '\0' || token[1] == '\0')
    {
      return false;
    }

    if (toupper(static_cast<unsigned char>(token[0])) != expectedPrefix)
    {
      return false;
    }

    char *endPtr = nullptr;
    const float parsed = strtof(token + 1, &endPtr);
    if (endPtr == token + 1 || *endPtr != '\0')
    {
      return false;
    }

    value = parsed;
    return true;
  }

  uint8_t toDirection(int32_t signedSteps)
  {
    return (signedSteps >= 0) ? FORWARD : BACKWARD;
  }

  uint32_t absU32(int32_t value)
  {
    const int32_t absoluteValue = (value >= 0) ? value : -value;
    return static_cast<uint32_t>(absoluteValue);
  }

  void releaseMotors()
  {
    leftMotor.release();
    rightMotor.release();
  }

  void moveServoUs(uint16_t pulseWidthUs)
  {
    if (pulseWidthUs < kServoMinUs)
    {
      pulseWidthUs = kServoMinUs;
    }
    if (pulseWidthUs > kServoMaxUs)
    {
      pulseWidthUs = kServoMaxUs;
    }

    penServo.writeMicroseconds(pulseWidthUs);
    currentServoUs = pulseWidthUs;
    delay(kServoSettleMs);
  }

  uint8_t computeStepDelayMs(float leftDeltaMm, float rightDeltaMm, float feedMmPerMin)
  {
    if (feedMmPerMin <= 1.0f)
    {
      return kDefaultStepDelayMs;
    }

    const float leftDeltaAbsMm = fabsf(leftDeltaMm);
    const float rightDeltaAbsMm = fabsf(rightDeltaMm);
    const float moveDistanceMm = (leftDeltaAbsMm > rightDeltaAbsMm) ? leftDeltaAbsMm : rightDeltaAbsMm;

    if (moveDistanceMm < 0.0001f)
    {
      return kDefaultStepDelayMs;
    }

    const float maxStepCount = moveDistanceMm * stepsPerMm();
    if (maxStepCount < 1.0f)
    {
      return kDefaultStepDelayMs;
    }

    const float totalMoveTimeMs = (moveDistanceMm / feedMmPerMin) * 60000.0f;
    float delayMs = totalMoveTimeMs / maxStepCount;

    if (delayMs < static_cast<float>(kMinStepDelayMs))
    {
      delayMs = static_cast<float>(kMinStepDelayMs);
    }
    if (delayMs > static_cast<float>(kMaxStepDelayMs))
    {
      delayMs = static_cast<float>(kMaxStepDelayMs);
    }

    return static_cast<uint8_t>(delayMs + 0.5f);
  }

  bool executeStepMove(int32_t leftTargetSteps,
                       int32_t rightTargetSteps,
                       uint8_t stepDelayMs)
  {
    const int32_t leftDelta = leftTargetSteps - currentLeftSteps;
    const int32_t rightDelta = rightTargetSteps - currentRightSteps;

    const uint32_t leftAbs = absU32(leftDelta);
    const uint32_t rightAbs = absU32(rightDelta);

    if (leftAbs > kMaxMoveStepsPerMotor || rightAbs > kMaxMoveStepsPerMotor)
    {
      Serial.println(F("ERR move too large"));
      return false;
    }

    const uint32_t totalSteps = (leftAbs > rightAbs) ? leftAbs : rightAbs;
    if (totalSteps == 0)
    {
      Serial.println(F("OK no movement"));
      return true;
    }

    if (stepDelayMs < kMinStepDelayMs)
    {
      stepDelayMs = kMinStepDelayMs;
    }
    if (stepDelayMs > kMaxStepDelayMs)
    {
      stepDelayMs = kMaxStepDelayMs;
    }

    const uint8_t leftDirection = toDirection(leftDelta);
    const uint8_t rightDirection = toDirection(rightDelta);
    uint32_t leftAccumulator = 0;
    uint32_t rightAccumulator = 0;

    for (uint32_t i = 0; i < totalSteps; ++i)
    {
      leftAccumulator += leftAbs;
      if (leftAccumulator >= totalSteps)
      {
        leftAccumulator -= totalSteps;
        leftMotor.onestep(leftDirection, SINGLE);
      }

      rightAccumulator += rightAbs;
      if (rightAccumulator >= totalSteps)
      {
        rightAccumulator -= totalSteps;
        rightMotor.onestep(rightDirection, SINGLE);
      }

      delay(stepDelayMs);
    }

    currentLeftSteps = leftTargetSteps;
    currentRightSteps = rightTargetSteps;
    releaseMotors();
    Serial.println(F("ok"));
    return true;
  }

  bool handleMoveCommand(char *params)
  {
    float targetLeftMm = 0.0f;
    float targetRightMm = 0.0f;
    float feedMmPerMin = 0.0f;
    bool hasL = false;
    bool hasR = false;
    bool hasF = false;

    char emptyParams[] = "";
    char *parseStart = (params != nullptr) ? params : emptyParams;
    char *savePtr = nullptr;
    for (char *token = strtok_r(parseStart, " \t", &savePtr);
         token != nullptr;
         token = strtok_r(nullptr, " \t", &savePtr))
    {
      float parsed = 0.0f;
      if (parseFloatToken(token, 'L', parsed))
      {
        targetLeftMm = parsed;
        hasL = true;
        continue;
      }
      if (parseFloatToken(token, 'R', parsed))
      {
        targetRightMm = parsed;
        hasR = true;
        continue;
      }
      if (parseFloatToken(token, 'F', parsed))
      {
        if (parsed <= 0.0f)
        {
          Serial.println(F("ERR F must be > 0"));
          return false;
        }
        feedMmPerMin = parsed;
        hasF = true;
        continue;
      }

      Serial.print(F("ERR bad token: "));
      Serial.println(token);
      return false;
    }

    if (!hasL || !hasR)
    {
      Serial.println(F("ERR G0/G1 requires L and R"));
      return false;
    }

    const int32_t leftTargetSteps = static_cast<int32_t>(lroundf(targetLeftMm * stepsPerMm()));
    const int32_t rightTargetSteps = static_cast<int32_t>(lroundf(targetRightMm * stepsPerMm()));

    if (leftTargetSteps < 0 || rightTargetSteps < 0)
    {
      Serial.println(F("ERR negative lengths not allowed"));
      return false;
    }

    const float currentLeftMm = static_cast<float>(currentLeftSteps) / stepsPerMm();
    const float currentRightMm = static_cast<float>(currentRightSteps) / stepsPerMm();
    const uint8_t stepDelayMs = hasF
                                    ? computeStepDelayMs(targetLeftMm - currentLeftMm,
                                                         targetRightMm - currentRightMm,
                                                         feedMmPerMin)
                                    : kDefaultStepDelayMs;

    return executeStepMove(leftTargetSteps, rightTargetSteps, stepDelayMs);
  }

  bool handleServoCommand(char *params)
  {
    float servoPulse = static_cast<float>(kServoDefaultUs);
    bool hasS = false;

    char emptyParams[] = "";
    char *parseStart = (params != nullptr) ? params : emptyParams;
    char *savePtr = nullptr;
    for (char *token = strtok_r(parseStart, " \t", &savePtr);
         token != nullptr;
         token = strtok_r(nullptr, " \t", &savePtr))
    {
      float parsed = 0.0f;
      if (parseFloatToken(token, 'S', parsed))
      {
        servoPulse = parsed;
        hasS = true;
        continue;
      }

      Serial.print(F("ERR bad token: "));
      Serial.println(token);
      return false;
    }

    if (!hasS)
    {
      Serial.println(F("ERR M300 requires S"));
      return false;
    }

    moveServoUs(static_cast<uint16_t>(lroundf(servoPulse)));
    Serial.println(F("ok"));
    return true;
  }

  bool executeCommandLine(char *line)
  {
    while (*line == ' ' || *line == '\t')
    {
      ++line;
    }

    if (*line == '\0')
    {
      return true;
    }

    char *comment = strchr(line, ';');
    if (comment != nullptr)
    {
      *comment = '\0';
    }

    if (*line == ';' || *line == '#')
    {
      return true;
    }

    char *savePtr = nullptr;
    char *command = strtok_r(line, " \t", &savePtr);
    if (command == nullptr)
    {
      return true;
    }

    for (char *ptr = command; *ptr != '\0'; ++ptr)
    {
      *ptr = static_cast<char>(toupper(static_cast<unsigned char>(*ptr)));
    }

    if ((strcmp(command, "G0") == 0) || (strcmp(command, "G1") == 0))
    {
      return handleMoveCommand(savePtr);
    }

    if (strcmp(command, "M300") == 0)
    {
      return handleServoCommand(savePtr);
    }

    Serial.print(F("ERR unsupported command: "));
    Serial.println(command);
    return false;
  }

  void processSerialInput()
  {
    while (Serial.available() > 0)
    {
      const char incoming = static_cast<char>(Serial.read());

      if (incoming == '\r')
      {
        continue;
      }

      if (incoming == '\n')
      {
        commandBuffer[commandLength] = '\0';
        executeCommandLine(commandBuffer);
        commandLength = 0;
        continue;
      }

      if (commandLength < (kCommandBufferLength - 1))
      {
        commandBuffer[commandLength++] = incoming;
      }
      else
      {
        Serial.println(F("ERR line too long"));
        commandLength = 0;
      }
    }
  }
}

void setup()
{
  Serial.begin(115200);
  Serial.println(F("Vertical plotter controller"));
  Serial.println(F("Ready: supported commands are G0, G1, M300."));

  penServo.attach(kServoPin);
  penServo.writeMicroseconds(kServoDefaultUs);
  currentServoUs = kServoDefaultUs;
  delay(kServoSettleMs);

  leftMotor.setSpeed(kStepperRpm);
  rightMotor.setSpeed(kStepperRpm);
  releaseMotors();
}

void loop()
{
  processSerialInput();
}
