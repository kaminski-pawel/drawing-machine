# Free notes

## Appropriate driver

I read [this discussion](https://forum.arduino.cc/t/confused-by-stepper-motor-powering/704013). The maker tried to use L298 driver for nema17 stepper motor. More experienced user pointed out:
> only some steppers can be driven with this kind of driver.
[...]
> That motor has has 1.7 ohm coils, meaning it tries to draw 12/1.7= 7Amp per phase on a 12volt supply.
> That eventually will burn out the supply or the L298 or the motor.
> This stepper needs a special current (not voltage) controlled stepper driver, like the DRV8825, set to <=1.2Amp.

## History 

Acc. to [this source](https://lizmelchor.com/wall-robot/?v=7d0db380a5b9), one of the earliest notable wall drawing robots, known as [Hektor](https://juerglehni.com/works/hektor), was created by artist Jürg Lehni in 2003.
