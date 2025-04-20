import logging
import pickle
import time
from typing import Dict, Tuple

import requests

import prowl

LAT: float = <MY_LATITUDE>
LONG: float = <MY_LONGITUDE>
ws: requests.Session = requests.Session()


def get_weather() -> Dict:
    logging.debug("Getting current weather")
    global ws
    url = "https://api.openweathermap.org/data/2.5/weather?zip=XXXXX,us&"
    url += "appid=<MY_OPENWEATHERAPI_KEY_HERE"
    try:
        r = ws.get(
            url,
            timeout=10,
            headers={"X-Clacks-Overhead": "GNU Terry Pratchett"},
        )
        retDict = r.json()
        r.close()
        return retDict
    except Exception as ex:
        logging.error(f"Unable to get weather data: {ex}")
        return {}


def get_aqi() -> Dict:
    logging.debug("Getting current AQI")
    global ws
    url = f"https://api.airvisual.com/v2/nearest_city?lat={LAT}&lon={LONG}&"
    url += "key=<MY_AIRVISUAL_KEY_HERE>"
    try:
        r = ws.get(
            url,
            timeout=10,
            headers={"X-Clacks-Overhead": "GNU Terry Pratchett"},
        )
        retDict = r.json()
        r.close()
        return retDict
    except Exception as ex:
        logging.error(f"Unable to get AQI data: {ex}")
        return {}


def get_alerts() -> Dict:
    logging.debug("Getting current weather alerts")
    global ws
    headers = {
        "User-Agent": "RPiClockWeather, <MY_EMAIL_ADD_HERE>",
        "X-Clacks-Overhead": "GNU Terry Pratchett",
    }
    url = "https://api.weather.gov/alerts/active?status=actual"
    url += f"&point={LAT},{LONG}"
    try:
        r = ws.get(url, timeout=10, headers=headers)
        retDict = r.json()
        r.close()
        return retDict
    except Exception as ex:
        logging.error(f"Unable to get alert data: {ex}")
        return {}


def pull_alerts() -> None:
    logging.debug("Entering pull_alerts")
    try:
        logging.debug("Reading the prior alerts")
        oldalerts = pickle.load(open("/home/pi/Chimes/walerts.pickle", "rb"))
    except Exception as ex:
        logging.warning(f"Error reading existing alerts: {ex}")
        oldalerts = []
    alerts = get_alerts()
    if alerts == {}:
        return
    if "features" in alerts:
        logging.info("Weather alerts found")
        for alt in alerts["features"]:
            alert = alt["properties"]
            if alert["status"] != "Actual":
                continue
            if alt in oldalerts:
                continue
            logging.info(f"New alert {alert} found")
            oldalerts.append(alt)
            endtime = time.strptime(alert["expires"], "%Y-%m-%dT%H:%M:%S%z")
            starttime = time.strptime(alert["onset"], "%Y-%m-%dT%H:%M:%S%z")
            subject = alert["event"]
            body = alert["headline"]
            severity = alert["severity"]
            msg = "UPDATED ALERT\n" if alert["messageType"] == "Update" else ""
            msg += f"From {time.asctime(starttime)} to {time.asctime(endtime)}"
            msg += f"\n{body}"
            if severity == "Severe":
                priority = 2
            else:
                priority = 0
            prowl.sendAlert(
                msg,
                priority,
                app="BigBen Weather Alerts",
                event=subject,
            )
    else:
        alerts["features"] = []
    newalerts = []
    for alert in oldalerts:
        if alert not in alerts["features"]:
            continue
        newalerts.append(alert)
    try:
        pickle.dump(
            newalerts, open("/home/pi/Chimes/walerts.pickle", "wb"), -1
        )
        logging.debug("Wrote new alerts file")
    except Exception as ex:
        logging.warning(f"Error writing alerts file: {ex}")


def get_temperature() -> Tuple[float, int]:
    logging.debug("Entering get_temperature")
    weather = get_weather()
    caqi = get_aqi()
    # Only pull alerts at the top of the hour
    if time.localtime().tm_min < 5:
        pull_alerts()
    curraqi = -1000
    if "data" in caqi:
        try:
            curraqi = int(caqi["data"]["current"]["pollution"]["aqius"])
            logging.debug(f"Current AQI is {curraqi}")
        except Exception as ex:
            logging.error(f"Unable to parse AQI: {ex}")
            curraqi = -1000
    if "main" in weather:
        try:
            logging.debug(f"Current weather is {weather}")
            return (
                float(weather["main"].get("temp", -1273.15)) - 273.15,
                curraqi,
            )
        except Exception as ex:
            logging.error(f"Unable to get weather: {ex}")
            return (-1000.0, curraqi)
    return (-1000.0, curraqi)
