# Vertical Plotter Machine

## Project description

A compact, hanging plotter that draws on a board by moving a pen carriage vertically and controlling pen contact with a micro-servo. The design uses two NEMA-17 stepper-driven spindles with a timing belt to raise/lower the carriage evenly, an Arduino Uno with an L293D shield for motor control.

## Parts

### Part list

| Part                                                       | Note                       | Qty |
| ---------------------------------------------------------- | -------------------------- | --- |
| Arduino Uno R3                                             | AVR ATMEL                  | 1   |
| L293D Motor Driver Shield Stepper Motor Driver for Arduino | copy of Adafruit Shield v1 | 1   |
| SG92R Micro Servo Motor                                    | working voltage 4.8-6.0 V  | 1   |
| NEMA-17 Stepper Motor KS42STH40-1204A                      | phase current: 1.2A        | 2   |
| AC to DC Adapter for power supply                          | current: 2A                | 1   |
| Timing Belt Pulley                                         |                            | 2   |
| Timing Belt 6mm                                            |                            | 1   |

### Detailed Specification

* L293D Motor Driver Shield Stepper Motor Driver
  - 2x L293D driver IC
  - 1x 74HC595 shift register
  - motor power supply terminal 4.5-25VDC
  - power supply selection PWR jumper
  - 4x H bridges: per bridge provides 0.6A (1.2A peak current) with thermal protection, can run motors on 4.5V to 12V DC
* SG92R Micro Servo Motor
  - working voltage 4.8-6.0V
  - 180 degree at PWM 500-2500µs
  - 90 degree at PWM 1000-2000µs
  - pulse width range 500-2500µs
  - neutral position 1500µs
* NEMA-17 Stepper Motor KS42STH40-1204A
  - phase current: 1.2A
  - phase resistance: 1.7 ohm
  - standard Voltage: 2V with active current limiting built-in and allow for the motors to be driven from voltages much higher than their rated voltage
  - 4-wire bipolar operation
* AC to DC Adapter for power supply
  - output current: 2A max
  - wattage: 24 watts
  - adjustable DC output voltage: 3V 4.5V 5V 6V 7.5V 9V 12V

## Resources

* [List of drawing robots](https://github.com/msurguy/awesome-drawing-robots)
