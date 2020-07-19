#!/usr/bin/python3 -O

import RPi.GPIO as GPIO
from PIL import Image, ImageDraw, ImageFont
import ST7789 as ST7789
from time import sleep, localtime
from pygame import mixer
from threading import Thread
import syslog
import weather


audio_config = {
    5: "volume_up",
    6: "volume_down",
    16: "mute",
    20: "future",
}

dispdict = {
    "handle_mute": handle_mute,
    "handle_volume_up": handle_volume_up,
    "handle_volume_down": handle_volume_down,
    "handle_future": handle_future,
}


def log(msg: str) -> None:
    syslog.openlog("pyClock")
    syslog.syslog(msg)
    syslog.closelog()


def gpio_event(pin: int) -> None:
    handler_name = f"handle_{audio_config[pin]}"
    dispdict[handler_name]()


def set_volume(volume: int) -> None:
    global qh
    global hh
    global tqh
    global hc
    global hcc
    global ChimeVolume
    ChimeVolume = volume
    if volume > 0:
        volume = float(volume) / 100.0
    else:
        volume = 0
    qh.set_volume(volume)
    hh.set_volume(volume)
    tqh.set_volume(volume)
    hc.set_volume(volume)
    hcc.set_volume(volume * 0.8)


# Yeah, this is pointless.
def get_volume() -> int:
    global ChimeVolume
    return ChimeVolume


def handle_mute() -> None:
    global PLAY_STATE
    global ChimeVolume
    global MuteVolume
    PLAY_STATE = not PLAY_STATE
    if PLAY_STATE:
        set_volume(MuteVolume)
    else:
        MuteVolume = ChimeVolume
        set_volume(0)


def handle_future() -> None:
    # Stub function for future use.
    pass


def handle_volume_up() -> None:
    set_volume(min(get_volume() + 5, 100))


def handle_volume_down() -> None:
    set_volume(max(get_volume() - 5, 0))


def play_chimes(hour: int, minute: int) -> None:
    global temp
    global PLAY_STATE
    if not PLAY_STATE:
        oldtemp = temp
        temp = weather.get_temperature()
        if temp < -100:
            temp = oldtemp
        return
    global qh
    global hh
    global tqh
    global hc
    global hcc
    if minute == 15:
        qh.play()
        sleep(qh.get_length())
    elif minute == 30:
        hh.play()
        sleep(hh.get_length())
    elif minute == 45:
        tqh.play()
        sleep(tqh.get_length())
    else:
        hc.play()
        sleep(hc.get_length())
        count = hour % 12
        if count == 0:
            count = 12
        for i in range(count):
            hcc.play()
            sleep(4.29)
    oldtemp = temp
    temp = weather.get_temperature()
    if temp < -100:
        temp = oldtemp
    return


def main():
    global PLAY_STATE
    PLAY_STATE = True

    # Initialize the sound
    mixer.pre_init()
    mixer.init()

    # Load the sounds
    # Set this to the directory you installed the app in
    chimedir = "/home/pi/Chimes/"

    # Download the chime sounds you want to use and rename
    # these sound file names to match your sounds.
    global qh
    qh = mixer.Sound("%sQuarterHourChime.wav" % chimedir)
    global hh
    hh = mixer.Sound("%sHalfHourChime.wav" % chimedir)
    global tqh
    tqh = mixer.Sound("%s3QuarterChime.wav" % chimedir)
    global hc
    hc = mixer.Sound("%sHourChime.wav" % chimedir)
    global hcc
    hcc = mixer.Sound("%sHourCountChime.wav" % chimedir)
    global ChimeVolume
    ChimeVolume = 40
    set_volume(ChimeVolume)

    # Initialize the buttons
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    for pin in audio_config:
        GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.add_event_detect(
            pin, GPIO.FALLING, callback=gpio_event, bouncetime=150
        )

    # Initialize the weather
    global temp
    temp = weather.get_temperature()
    if temp < -100:
        temp = 0

    # Initialize the image
    # Download the image you want to use as a backgroound
    # and rename this variable appropriately.
    image_file = f"{chimedir}/bigben.jpg"
    # Change this to point at the font yuou want to use
    FONT = "pygame/examples/data/sans.ttf"
    ttf = ImageFont.truetype(FONT, 50,)
    dttf = ImageFont.truetype(FONT, 40,)

    # Create ST7789 LCD display class.
    disp = ST7789.ST7789(
        rotation=90, port=0, cs=1, dc=9, backlight=13, spi_speed_hz=90000000,
    )

    # Initialize display.
    disp.begin()

    WIDTH = disp.width
    HEIGHT = disp.height

    # Load an image.
    image = Image.open(image_file)

    # Resize the image and display the initial clock
    image = image.resize((WIDTH, HEIGHT))
    draw = ImageDraw.Draw(image)
    curtime = localtime()
    ap = "AM" if curtime.tm_hour < 12 else "PM"
    hour = curtime.tm_hour % 12
    if hour == 0:
        hour = 12
    fahr = int((temp * 9.0) / 5.0) + 32
    draw.text((20, 170), f"{fahr}F {temp:.1f}C", font=dttf)
    draw.text((15, 90), f"{hour:02}:{curtime.tm_min:02} {ap}", font=ttf)
    date = localtime()
    # People outside the US will want to change this format
    draw.text(
        (20, 20),
        f"{date.tm_mon:02}/{date.tm_mday:02}/{date.tm_year}",
        font=dttf,
    )
    disp.display(image)

    while True:
        image = Image.open(image_file)
        image = image.resize((WIDTH, HEIGHT))
        draw = ImageDraw.Draw(image)
        while localtime().tm_sec > 0:
            sleep(1)
        curtime = localtime()
        hour = curtime.tm_hour % 12
        minute = curtime.tm_min
        ap = "AM" if curtime.tm_hour < 12 else "PM"
        if hour == 0:
            hour = 12
        fahr = int((temp * 9.0) / 5.0) + 32
        draw.text((30, 170), f"{fahr}F {temp:.1f}C", font=dttf)
        draw.text((15, 90), f"{hour:02}:{minute:02} {ap}", font=ttf)
        date = localtime()
        # People outside the US will want to change this format
        draw.text(
            (20, 20),
            f"{date.tm_mon:02}/{date.tm_mday:02}/{date.tm_year}",
            font=dttf,
        )
        disp.display(image)
        if minute % 15 == 2 and "chimeThread" in locals():
            chimeThread.join(1.0)  # noqa: F821
            del chimeThread
        if minute % 15 == 0:
            chimeThread = Thread(target=play_chimes, args=(hour, minute))
            chimeThread.start()
        sleep(2)


if __name__ == "__main__":
    log("Starting Pirate Audio Clock")
    main()
