import http.server
import logging
import unittest
from json import dumps as jdumps
from sys import exit as sysexit
from threading import Thread
from time import asctime, localtime, sleep
from typing import Any, Callable, Dict, Optional, Union
from unittest.mock import patch
from urllib.parse import parse_qs

import RPi.GPIO as GPIO
import ST7789 as ST7789
from PIL import Image, ImageDraw, ImageFont
from pygame import mixer

import weather

audio_config: Dict[int, str] = {
    5: "volume_up",
    6: "volume_down",
    16: "mute",
    20: "future",
}

# Initialize the global variables so lint is happy
PORT: int = 8000
hostname: str = ""
PLAY_STATE: bool = True
qh: Optional[mixer.SoundType] = None
hh: Optional[mixer.SoundType] = None
tqh: Optional[mixer.SoundType] = None
hc: Optional[mixer.SoundType] = None
hcc: Optional[mixer.SoundType] = None
ChimeVolume: int = 0
MuteVolume: int = 0
temp: float = 0.0
AQI: int = 0
VolumeMax: int = 100
DefaultVolume: int = 70
num_reqs: int = 0


def set_volume(volume: int) -> None:
    logging.debug(f"Entering set_volume to {volume}")
    global qh
    global hh
    global tqh
    global hc
    global hcc
    global ChimeVolume
    global VolumeMax
    ChimeVolume = volume
    volume = min(max(volume, 0), VolumeMax)
    logging.debug(f"Setting volume to {volume}")
    qh.set_volume(round(float(volume) * 0.9))
    hh.set_volume(volume)
    tqh.set_volume(volume)
    hc.set_volume(volume)
    hcc.set_volume(round(float(volume) * 0.8))


class MyServer(http.server.BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        logging.debug("Handing HTTP GET request")
        global temp
        global ChimeVolume
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        query: Dict[Union[bytes, str], Any] = parse_qs(self.path)
        logging.debug(f"query={query}")
        htemp: float = ((float(temp) * 9.0) / 5.0) + 32.0
        if "/volume" in query:
            try:
                set_volume(int(query["/volume"][0]))
            except Exception as ex:
                logging.info(f"Passed in bad volume {query['/volume']}")
        hout: Dict[str, Any] = {
            "temperature": htemp,
            "aqi": AQI,
            "time": asctime(),
            "volume": ChimeVolume,
        }
        hout.update(query)
        jdata: str = jdumps(hout)
        logging.debug(f"payload={jdata}")
        self.wfile.write(bytes(jdata, "utf-8"))


def serverThread() -> None:
    global hostname
    global PORT
    logging.debug(f"Starting HTTP server on port {PORT}")
    while True:
        webServer: http.server.HTTPServer = http.server.HTTPServer(
            (hostname, PORT), MyServer
        )
        try:
            webServer.serve_forever()
        except Exception as ex:
            logging.error(f"webServer had unexpected error: {ex}")
        logging.info("Restarting webServer for some reason.")
        try:
            webServer.shutdown()
            webServer.server_close()
            sleep(5)
        except Exception as ex:
            logging.error(f"Error shutting down webServer: {ex}")
            sysexit(-1)


class TestServerThreadFunction(unittest.TestCase):
    @patch("http.server.HTTPServer")
    @patch("time.sleep", side_effect=InterruptedError)  # To break the infinite loop
    def test_server_thread_starts_serve_forever(self, mock_sleep, mock_server):
        with self.assertRaises(InterruptedError):
            serverThread()
        mock_server.assert_called_with((hostname, PORT), MyServer)
        mock_server.return_value.serve_forever.assert_called_once()

    @patch("http.server.HTTPServer")
    def test_server_thread_handles_exception(self, mock_server):
        mock_server.return_value.serve_forever.side_effect = Exception(
            "Unexpected Error"
        )
        with (
            patch("logging.error") as mock_logging_error,
            patch("time.sleep", side_effect=InterruptedError),
        ):  # To simulate server failure and break loop
            with self.assertRaises(InterruptedError):
                serverThread()
            mock_logging_error.assert_called_with(
                "webServer had unexpected error: Unexpected Error"
            )


def get_volume() -> int:
    global ChimeVolume
    return ChimeVolume


def handle_mute() -> None:
    logging.debug("Toggling mute")
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
    logging.debug("Increasing volume")
    global VolumeMax
    set_volume(min(get_volume() + 5, VolumeMax))


def handle_volume_down() -> None:
    logging.debug("Decreasing volume")
    set_volume(max(get_volume() - 5, 0))


def gpio_event(pin: int) -> None:
    dispdict: Dict[str, Callable[[], None]] = {
        "handle_mute": handle_mute,
        "handle_volume_up": handle_volume_up,
        "handle_volume_down": handle_volume_down,
        "handle_future": handle_future,
    }
    handler_name = f"handle_{audio_config[pin]}"
    dispdict[handler_name]()


def play_chimes(hour: int, minute: int) -> None:
    global temp
    global PLAY_STATE
    global AQI
    if not PLAY_STATE:
        # If we're muted, just get the temp and leave.
        oldtemp = temp
        oldaqi = AQI
        temp, AQI = weather.get_temperature()
        if temp < -100:
            temp = oldtemp
        if AQI < -100:
            AQI = oldaqi
        return
    global qh
    global hh
    global tqh
    global hc
    global hcc
    if minute == 15:
        logging.debug("Playing quarter hour chimes")
        qh.play()
        sleep(qh.get_length())
    elif minute == 30:
        logging.debug("Playing half hour chimes")
        hh.play()
        sleep(hh.get_length())
    elif minute == 45:
        logging.debug("Playing three-quarter hour chimes")
        tqh.play()
        sleep(tqh.get_length())
    else:
        # The sleep values below were derived from listening to multiple
        # recordings of the Victoria Tower bells. This should accurately
        # reflect the actual sound of the clock chimes.
        sleep(35)
        logging.debug("Playing hour chime")
        hc.play()
        sleep(22)
        # Yes, this is a high CPU busy wait. We want to start as close to
        # sec=0 as possible.
        while localtime().tm_sec > 0:
            continue
        count = (hour + 1) % 12
        if count == 0:  # This accounts for midnight also
            count = 12
        logging.debug(f"Playing {count} hour bells")
        for i in range(count):
            hcc.play()
            sleep(4.29)
    # Pull the temp at the end so we don't disrupt the bell chimes.
    oldtemp = temp
    oldaqi = AQI
    temp, AQI = weather.get_temperature()
    if temp < -100:
        temp = oldtemp
    if AQI < -100:
        AQI = oldaqi
    return


def main():
    global PLAY_STATE
    PLAY_STATE = True

    # Define the AQI colors
    colors = [
        "#FFFFFF",  # White
        "yellow",
        "#FFA500",  # Orange
        "red",
        "purple",
        "#800000",  # Maroon
    ]

    # Initialize the sound
    logging.debug("Initializing the sound mixer")
    mixer.pre_init()
    mixer.init()

    # Load the sounds
    logging.debug("Loading the sound files")
    chimedir = "/home/pi/Chimes/"
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
    global DefaultVolume
    set_volume(DefaultVolume)

    # Initialize the buttons
    logging.debug("Initializing the physical buttons")
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    for pin in audio_config:
        GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.add_event_detect(pin, GPIO.FALLING, callback=gpio_event, bouncetime=150)

    # Initialize the weather
    logging.debug("Initializing the weather")
    global temp
    global AQI
    temp, AQI = weather.get_temperature()
    if temp < -100:
        temp = 0
    if AQI < -100:
        AQI = 0

    # Initialize the image
    image_file = "/home/pi/Chimes/bigben.jpg"
    ttf = ImageFont.truetype(
        "/home/pi/Chimes/sans.ttf",
        50,
    )
    dttf = ImageFont.truetype(
        "/home/pi/Chimes/sans.ttf",
        40,
    )

    # Create ST7789 LCD display class.
    logging.debug("Configuring the display")
    disp = ST7789.ST7789(
        rotation=90,
        port=0,
        cs=1,
        dc=9,
        backlight=13,
        spi_speed_hz=90000000,
    )

    # Initialize display.
    logging.debug("Initializing the display")
    disp.begin()

    WIDTH = disp.width
    HEIGHT = disp.height

    # Load an image.
    logging.debug("Loading the initial background image")
    image = Image.open(image_file)

    # Resize the image and display the initial clock
    logging.debug("Creating the initial time/date/weather display image")
    image = image.resize((WIDTH, HEIGHT))
    draw = ImageDraw.Draw(image)
    logging.debug("Getting the time")
    curtime = localtime()
    ap = "AM" if curtime.tm_hour < 12 else "PM"
    hour = curtime.tm_hour % 12
    if hour == 0:
        hour = 12
    fahr = round((temp * 9.0) / 5.0) + 32
    logging.debug("Writing the time/date/weather to the initial image")
    draw.text((20, 190), f"{fahr}F {temp:.1f}C", font=dttf)
    draw.text((15, 65), f"{hour:02}:{curtime.tm_min:02} {ap}", font=ttf)
    draw.text((50, 125), f"AQI {AQI}", font=ttf, fill=colors[AQI // 50])
    draw.text(
        (20, 20),
        f"{curtime.tm_mon:02}/{curtime.tm_mday:02}/{curtime.tm_year}",
        font=dttf,
    )
    logging.debug("Displaying the initial image")
    disp.display(image)

    http_thread = Thread(target=serverThread, daemon=True)
    http_thread.start()

    while True:
        logging.debug("Loading new background image")
        image = Image.open(image_file)
        image = image.resize((WIDTH, HEIGHT))
        draw = ImageDraw.Draw(image)
        while localtime().tm_sec < 58:
            sleep(0.97)
        # Another high CPU busy wait. Same reason.x
        while localtime().tm_sec > 0:
            continue
        logging.debug("Getting the time")
        curtime = localtime()
        hour = curtime.tm_hour % 12
        minute = curtime.tm_min
        if minute % 15 == 0 or minute == 59:
            if minute != 0:
                chimeThread = Thread(target=play_chimes, args=(hour, minute))
                chimeThread.start()
        ap = "AM" if curtime.tm_hour < 12 else "PM"
        if hour == 0:
            hour = 12
        fahr = round((temp * 9.0) / 5.0) + 32
        logging.debug("Writing the time/date/weather to the image")
        draw.text((20, 190), f"{fahr}F {temp:.1f}C", font=dttf)
        draw.text((15, 65), f"{hour:02}:{minute:02} {ap}", font=ttf)
        draw.text((50, 125), f"AQI {AQI}", font=ttf, fill=colors[AQI // 50])
        draw.text(
            (20, 20),
            f"{curtime.tm_mon:02}/{curtime.tm_mday:02}/{curtime.tm_year}",
            font=dttf,
        )
        logging.debug("Displaying the latest image")
        disp.display(image)
        if minute % 15 == 2 and "chimeThread" in locals():
            chimeThread.join(1.0)  # noqa: F821
            del chimeThread
        sleep(2)


if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s %(levelname)s:\t%(message)s",
        level=logging.DEBUG,
    )
    logging.info("Starting Pirate Audio Clock")
    main()
