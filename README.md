# LED-Xray-scattering-clock
An LED clock display that simulates the 2D scattering profile of an oriented cylinder aligned with the hour hand. Uses 2 push buttons with press and hold functionality to change brightness, colormap, digital clock display, and to change the time. Time is kept when unplugged using RTC on Adafruit HAT. 3D printed stand stl files included.

Uses rpi-rgb-led-matrix by hzeller

## Details
Calculates the form factor of a cylinder oriented in-plane and aligned with the hour hand. The LED display thus mimics a X-ray detector for a typical SAXS/WAXS experiment. The parameters used in the simulation are shown below but can be changed:
- X-ray energy = 13.3 keV
- Sample to detector distance = 1.1 m
- Detector = 64 x 64 pixels, 3 mm each (size does not need to match LED display)
- Cylinder length = 30 nm
- Cylinder radius = 2 nm

## Usage
- Button 1 press: Cycle through digital clock display options (no display, display in 4 corners w/ & w/o black background)
- Button 1 hold: Enter set time mode
- Button 2 press: Cycle through brightness options
- Button 2 hold: Cycle through colormap options

To set time, hold button 1. Pressing Button 2 increments the current underlined number. Pressing Button 1 moves to the next number. Move through all numbers to finish.

## Images
<img src="https://github.com/JustinJKwok/LED-Xray-scattering-clock/blob/main/rod_saxs_led_display.jpg" width="450" height="600">
<img src="https://github.com/JustinJKwok/LED-Xray-scattering-clock/blob/main/rod_saxs_led_display_side.jpg" width="298" height="600">
