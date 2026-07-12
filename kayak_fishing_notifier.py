#!/usr/bin/env python3
"""
Kayak Fishing Weekend Notifier - Palmyra WA (v2)
Daily 4pm AWST check • Free Open-Meteo marine data • Moon phase aware
Notifies only once per ideal weekend
"""

import requests
import datetime as dt
import json
import smtplib
import os
import logging
from email.mime.text import MIMEText
from datetime import datetime, date

# ==================== CONFIG ====================
LOCATION = {"lat": -32.04, "lon": 115.78}  # Palmyra / Fremantle area

THRESHOLDS = {
    "max_wind_kmh": 20,
    "max_wave_m": 0.7,
    "max_precip_prob": 30,
    "min_temp_c": 10,
}

GMAIL_USER = os.getenv("GMAIL_USER")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
STATE_FILE = "notified_weekends.json"

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def get_moon_phase(d: date) -> str:
    """Simple pure-Python moon phase."""
    known_new_moon = date(1900, 1, 31).toordinal()
    lunar_cycle = 29.53058867
    days_since = (d.toordinal() - known_new_moon) % lunar_cycle
    if days_since < 1.84566:
        return "New Moon (good for some nocturnal feeders)"
    elif days_since < 7.382:
        return "Waxing Crescent"
    elif days_since < 14.765:
        return "First Quarter / Waxing Gibbous (often good activity)"
    elif days_since < 22.147:
        return "Full Moon (excellent night fishing potential)"
    elif days_since < 29.53:
        return "Waning Gibbous / Last Quarter"
    else:
        return "New Moon"


def get_forecast():
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": LOCATION["lat"],
        "longitude": LOCATION["lon"],
        "daily": ["temperature_2m_max", "temperature_2m_min",
                  "precipitation_probability_max", "windspeed_10m_max"],
        "timezone": "Australia/Perth",
        "forecast_days": 14
    }
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    data = r.json()

    marine_url = "https://marine-api.open-meteo.com/v1/marine"
    marine_params = {
        "latitude": LOCATION["lat"],
        "longitude": LOCATION["lon"],
        "daily": ["wave_height_max"],
        "timezone": "Australia/Perth",
        "forecast_days": 14
    }
    mr = requests.get(marine_url, params=marine_params, timeout=30)
    mr.raise_for_status()
    marine_data = mr.json()

    daily = []
    for i in range(14):
        day_date = dt.datetime.strptime(data["daily"]["time"][i], "%Y-%m-%d").date()
        daily.append({
            "date": data["daily"]["time"][i],
            "temp_max": data["daily"]["temperature_2m_max"][i],
            "temp_min": data["daily"]["temperature_2m_min"][i],
            "precip_prob": data["daily"]["precipitation_probability_max"][i],
            "wind_max_kmh": data["daily"]["windspeed_10m_max"][i],
            "wave_max_m": marine_data["daily"].get("wave_height_max", [0]*14)[i],
            "moon_phase": get_moon_phase(day_date),
        })
    return daily


def is_good_day(day):
    return (
        day["wind_max_kmh"] <= THRESHOLDS["max_wind_kmh"] and
        day["wave_max_m"] <= THRESHOLDS["max_wave_m"] and
        day["precip_prob"] <= THRESHOLDS["max_precip_prob"] and
        day["temp_min"] >= THRESHOLDS["min_temp_c"]
    )


def get_upcoming_weekends(daily_data):
    weekends = []
    seen = set()
    for i, day in enumerate(daily_data):
        d = dt.datetime.strptime(day["date"], "%Y-%m-%d").date()
        if d.weekday() in [4, 5]:
            start = day["date"]
            if start in seen:
                continue
            seen.add(start)
            end_idx = min(i + 2 if d.weekday() == 4 else i + 1, len(daily_data) - 1)
            weekends.append({"start_date": start, "days": daily_data[i:end_idx + 1]})
    return weekends


def is_ideal_weekend(weekend):
    return any(is_good_day(d) for d in weekend["days"])


def get_why_ideal(weekend):
    d = weekend["days"][0]
    if d["wind_max_kmh"] <= 12 and d["wave_max_m"] <= 0.4:
        window = "All day – conditions are exceptionally calm"
    else:
        window = "Early morning and late afternoon (dawn/dusk windows)"
    return (f"Key conditions: Wind max {d['wind_max_kmh']} km/h, "
            f"Wave max {d['wave_max_m']:.1f} m, Precip prob {d['precip_prob']}%, "
            f"Temps {d['temp_min']:.0f}–{d['temp_max']:.0f}°C. "
            f"Best fishing window: {window}. Moon phase: {d['moon_phase']}.")


def generate_species_paragraph(weekend):
    d = weekend["days"][0]
    wind = d["wind_max_kmh"]
    moon = d["moon_phase"]

    if wind <= 15:
        base = ("Calm winds and good visibility are excellent for black bream and yellowfin whiting around structure and shallow banks. "
                "Flathead are also likely to be active on the incoming tide. ")
    else:
        base = ("Moderate conditions still favour hardy species like black bream and tailor. "
                "Whiting and flathead will be more active during the calmer parts of the day. ")

    if "Full Moon" in moon or "New Moon" in moon:
        base += "The current moon phase often increases nocturnal and dawn/dusk activity for many estuary species."
    else:
        base += "Fishing pressure is usually moderate under the current moon phase."

    return base


def load_notified():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return []


def save_notified(notified_list):
    with open(STATE_FILE, "w") as f:
        json.dump(notified_list, f)


def send_email(subject, body):
    if not GMAIL_USER or not GMAIL_APP_PASSWORD:
        logging.error("Gmail credentials missing")
        return False
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = GMAIL_USER
    msg["To"] = GMAIL_USER
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_USER, GMAIL_USER, msg.as_string())
        logging.info("Email sent successfully")
        return True
    except Exception as e:
        logging.error(f"Email failed: {e}")
        return False


def main():
    logging.info("Starting daily kayak fishing check (v2)...")
    daily = get_forecast()
    weekends = get_upcoming_weekends(daily)
    notified = load_notified()

    new_ideal = None
    for w in weekends:
        if is_ideal_weekend(w) and w["start_date"] not in notified:
            new_ideal = w
            break

    if new_ideal:
        subject = f"🎣 Ideal Kayak Fishing Weekend Alert – {new_ideal['start_date']}"
        why = get_why_ideal(new_ideal)
        species = generate_species_paragraph(new_ideal)
        body = f"""Great news! The weekend starting {new_ideal['start_date']} looks ideal for kayak fishing in the Palmyra area.

{why}

{species}

Stay safe on the water and tight lines!"""

        if send_email(subject, body):
            notified.append(new_ideal["start_date"])
            save_notified(notified)
    else:
        logging.info("No new ideal weekends or already notified.")


if __name__ == "__main__":
    main()
