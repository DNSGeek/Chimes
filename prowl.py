#!/usr/bin/python3 -uO

import requests
import sys
import syslog
from platform import node

priorities = {"vlow": -2, "low": -1, "normal": 0, "high": 1, "emergency": 2}


def log(msg: str) -> None:
    syslog.openlog("pyProwl")
    syslog.syslog(msg)
    syslog.closelog()


def sendAlert(
    msg="Test", priority=0, app=node(), event="%s Event" % node(), url=""
):
    """Send a notification to Prowl. Priority is -2 (Very Low) to 2 (Emergency)."""
    # Set this to your ProwlApp API and Provider keys
    API = ""
    Provider = ""

    if len(url) > 0:
        params = {
            "apikey": API,
            "providerkey": Provider,
            "priority": priority,
            "url": url,
            "application": app,
            "event": event,
            "description": msg,
        }
    else:
        params = {
            "apikey": API,
            "providerkey": Provider,
            "priority": priority,
            "application": app,
            "event": event,
            "description": msg,
        }

    headers = {
        "Content-type": "application/x-www-form-urlencoded",
        "Accept": "text/plain",
    }

    try:
        r = requests.post(
            "https://api.prowlapp.com/publicapi/add/",
            data=params,
            headers=headers,
        )
        log(r.status_code)
        r.close()
        return []
    except Exception as ex:
        log("Error sending Prowl notification: %s" % str(ex))
        return []
