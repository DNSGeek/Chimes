# Pirate Audio Chiming Clock

This is a small Python 3 application that will display the current date, time and temperature over a background of your choosing. It was written for a Pirate Audio Raspberry Pi HAT <https://shop.pimoroni.com/collections/pirate-audio>

It will also send weather alerts to your phone and play clock chimes at :15, :30, :45 and the top of the hour, along with hour count chimes.

## Prerequisites
```
sudo apt install python3-rpi.gpio python3-pil python3-pygame python3-requests
```

If you haven't yet set up your Pirate Audio HAT, you'll need to do the following:
* The DAC can be configured by adding dtoverlay=hifiberry-dac to the /boot/config.txt file.
* There is a DAC enable pin—BCM 25— that must be driven high to enable the DAC. You can do this by adding gpio=25=op,dh to the /boot/config.txt file.
* The DAC audio can be configured by changing dtparam=audio=on to dtparam=audio=off to the /boot/config.txt file.

You will need to reboot your Pi after editing the /boot/config.txt file.

Install the ST7789 display driver from https://github.com/pimoroni/st7789-python

## Chimes and background
You will need to download a background image and the sound files you want to use for the fifteen, thirty, fourty-five and hour chimes, as well as a bell toll file to use for counting out the hour. Follow the instructions in the comments of pirate.py for where to put these files.

## Weather and alerts
Follow the instructions in weather.py to configure the weather for your location. You will need a Prowl developer ID to send the alerts to your phone. https://www.prowlapp.com/
