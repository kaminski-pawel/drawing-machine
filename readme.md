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
| Timing Belt Pulley GT2 20-tooth 5mm Bore Aluminium        | 6mm wide, 2mm pitch        | 2   |
| Timing Belt GT2 6mm                                        | 2mm pitch                  | 1   |

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
* [l293D shield tutorial](https://lastminuteengineers.com/l293d-motor-driver-shield-arduino-tutorial/)
* [example project operating on g-code files](https://www.instructables.com/Polargraph-Wall-Draw-Bot-2023/) using [grbl fork](https://github.com/john4242/grbl-polargraph)

## Connection test firmware

The firmware in [src/main.cpp](src/main.cpp) is a short hardware check for:

* left stepper on shield stepper port 1 (`M1 + M2`)
* right stepper on shield stepper port 2 (`M3 + M4`)
* servo on the shield servo header for `D10`

What the test does:

* centers the servo, then moves it to two safe pulse-width positions and back to center
* jogs the left stepper forward and backward
* jogs the right stepper forward and backward
* jogs both steppers together forward and backward
* releases the stepper coils between moves to limit heating

Run the test with the belt or carriage load removed if possible. Open the serial monitor at `115200` baud to follow the sequence.

## Powering the test

### Important electrical limit

The `L293D` shield in this project is **not a good long-term driver** for the listed `NEMA-17 KS42STH40-1204A` motors. The motors are rated for `1.2 A/phase`, while one `L293D` bridge is only about `0.6 A` continuous and the shield has **no current limiting**. Use the included test only as a brief connection check at low speed. If the motors get hot quickly, chatter loudly, or the shield overheats, cut power immediately.

### Recommended test power setup

Use two power sources during bring-up:

* `Arduino Uno`: power from `USB`
* `Motor shield EXT_PWR`: separate `4.5 V to 5 V DC` supply, current capability at least `2 A`
* `PWR jumper`: `OFF` / removed

Why this is the safest setup for this shield:

* the Arduino stays on a stable USB supply while the steppers inject noise into the motor supply
* the shield motor supply is isolated from the Arduino input path
* `4.5-5 V` is the lowest practical range supported by the shield's motor terminal and is less aggressive than `7.5-12 V` for these low-resistance motors

### EXT_PWR with Arduino powered separately

This is the mode you should use for the test.

* Connect the adjustable adapter `+` and `-` to the shield `EXT_PWR` screw terminal.
* Set the adapter to `4.5 V` first. If the motors only buzz and do not move, try `5 V`, but do not go higher for this shield-and-motor combination.
* Keep the `PWR` jumper removed.
* Keep the Uno connected to `USB` for logic power and uploading.

### EXT_PWR with Arduino board sharing the same motor supply

This is **not recommended** for this project.

* On this style of shield, the `PWR` jumper ties the motor supply rail to the Arduino power input path.
* Sharing that supply makes brownouts and resets more likely when the steppers start or when the servo moves.
* It also pushes you toward a higher shared input voltage for the Uno, which is exactly what these low-resistance steppers should avoid on an `L293D` shield.

If you still want a single-supply setup for experimentation, do it only briefly and monitor temperature closely. The better fix is to switch the steppers to a current-limited driver such as `A4988`, `DRV8825`, or another suitable stepper driver.

### PWR jumper summary

* `PWR jumper OFF`: use when `EXT_PWR` feeds only the motors and the Arduino is powered separately. This is the preferred test setup.
* `PWR jumper ON`: ties the motor power rail to the Arduino power path. Avoid this here unless you fully understand the shield wiring and accept the reset/overcurrent risk.

## Expected result

If all three actuators are connected correctly:

* the servo moves to center, one side, the other side, then back to center
* each stepper turns a small amount in one direction and then returns
* both steppers then turn together in the same direction and return

If one stepper moves in the wrong direction, reverse one coil pair on that motor connector or swap `FORWARD` and `BACKWARD` in [src/main.cpp](src/main.cpp).

## TODO

* Consider compact binary frames over serial. For now I've opted for text GCode-like over serial, as it is more readable (debuggable). Binary will be smaller and faster, though. 
