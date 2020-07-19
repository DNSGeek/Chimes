import requests
import time
from typing import Dict
import prowl
import pickle
import syslog


def log(msg: str) -> None:
    syslog.openlog("pyWeather")
    syslog.syslog(msg)
    syslog.closelog()


# Set this to your 5 digit zip code
# You'll need to modify this and the get_weather URL for non-US
ZIPCODE = ""

# Set this to your openweather app id
APPID = ""

# Set these to your latitude and longitude
LAT = ""
LONG = ""

# Change this directory to where you've installed this app
BASEDIR = ""


def get_weather() -> Dict:
    url = f"https://api.openweathermap.org/data/2.5/weather?zip={ZIPCODE},us&"
    url += f"appid={APPID}"
    try:
        r = requests.get(url, timeout=10)
        retDict = r.json()
        return retDict
    except Exception as ex:
        log(f"Unable to get weather data: {ex}")
        return {}


# Set MYWEATHERAPP and MYEMAIL to your values
def get_alerts() -> Dict:
    headers = {"User-Agent": "MYWEATHERAPP, MYEMAIL"}
    url = "https://api.weather.gov/alerts/active?status=actual"
    url += f"&point={LAT},{LONG}"
    try:
        r = requests.get(url, timeout=10, headers=headers)
        retDict = r.json()
        return retDict
    except Exception as ex:
        log(f"Unable to get alert data: {ex}")
        return {}


def pull_alerts() -> None:
    try:
        oldalerts = pickle.load(open(f"{BASEDIR}/walerts.pickle", "rb"))
    except Exception:
        oldalerts = []
    alerts = get_alerts()
    if alerts == {}:
        return
    if "features" in alerts:
        for alt in alerts["features"]:
            alert = alt["properties"]
            if alert["status"] != "Actual":
                continue
            if alt in oldalerts:
                continue
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
                priority=priority,
                msg=msg,
                app="BigBen Weather Alerts",
                event=subject,
                url=alert["@id"],
            )
    else:
        alerts["features"] = []
    newalerts = []
    for alert in oldalerts:
        if alert not in alerts["features"]:
            continue
        newalerts.append(alert)
    try:
        pickle.dump(newalerts, open(f"{BASEDIR}/walerts.pickle", "wb"), -1)
    except Exception:
        pass


def get_temperature() -> float:
    weather = get_weather()
    if time.localtime().tm_min < 5:
        pull_alerts()
    if "main" in weather:
        try:
            return float(weather["main"].get("feels_like", 1273.15)) - 273.15
        except Exception as ex:
            log(f"Unable to get feels_like weather: {ex}")
            return -1000.0
    return -1000.0
