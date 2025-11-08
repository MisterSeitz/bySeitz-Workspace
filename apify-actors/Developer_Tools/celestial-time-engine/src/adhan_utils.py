"""
adhan_utils.py — Extracted core logic from adhanpy 1.0.5
Lightweight internal replacement for adhanpy dependency.
"""

import math
from datetime import datetime, timedelta, date, timezone


# ------------------------------------------------------
# Constants & Base Calculation Classes
# ------------------------------------------------------

class AsrMethod:
    STANDARD = "STANDARD"
    HANAFI = "HANAFI"

    @staticmethod
    def get_method(name: str):
        name = name.upper()
        if name == "HANAFI":
            return AsrMethod.HANAFI
        return AsrMethod.STANDARD


class CalculationMethod:
    """Represents various pre-defined prayer time methods (matching adhanpy 1.x)."""

    METHODS = {
        "ISNA": {"fajr_angle": 15, "isha_angle": 15},
        "MuslimWorldLeague": {"fajr_angle": 18, "isha_angle": 17},
        "Makkah": {"fajr_angle": 18.5, "isha_interval": 90},
        "Egypt": {"fajr_angle": 19.5, "isha_angle": 17.5},
        "Karachi": {"fajr_angle": 18, "isha_angle": 18},
        "Tehran": {"fajr_angle": 17.7, "isha_angle": 14, "maghrib_angle": 4.5},
        "Jafari": {"fajr_angle": 16, "isha_angle": 14, "maghrib_angle": 4},
        "Turkey": {"fajr_angle": 13, "isha_angle": 13},
        "Dubai": {"fajr_angle": 18.2, "isha_angle": 18.2},
    }

    @staticmethod
    def get_params(method_name: str) -> dict:
        return CalculationMethod.METHODS.get(method_name, CalculationMethod.METHODS["ISNA"])


# ------------------------------------------------------
# Astronomical helpers
# ------------------------------------------------------

def _julian(date):
    return date.toordinal() + 1721424.5


def _sun_position(jd):
    D = jd - 2451545.0
    g = math.radians((357.529 + 0.98560028 * D) % 360)
    q = (280.459 + 0.98564736 * D) % 360
    L = (q + 1.915 * math.sin(g) + 0.020 * math.sin(2 * g)) % 360
    e = 23.439 - 0.00000036 * D
    RA = math.degrees(math.atan2(math.cos(math.radians(e)) * math.sin(math.radians(L)), math.cos(math.radians(L)))) / 15
    decl = math.degrees(math.asin(math.sin(math.radians(e)) * math.sin(math.radians(L))))
    return decl


def _time_diff(t1, t2):
    diff = t2 - t1
    if diff < 0:
        diff += 24
    return diff


def _sun_angle_time(angle, lat, decl, rising):
    lat_rad = math.radians(lat)
    decl_rad = math.radians(decl)
    angle_rad = math.radians(angle)
    val = (-math.sin(angle_rad) - math.sin(lat_rad) * math.sin(decl_rad)) / (math.cos(lat_rad) * math.cos(decl_rad))
    if val < -1 or val > 1:
        return None
    t = math.degrees(math.acos(val)) / 15.0
    return 12 - t if rising else 12 + t


def _hours_to_time(hours, date_obj, tz_offset):
    if hours is None:
        return None
    total_seconds = hours * 3600
    local_time = datetime.combine(date_obj, datetime.min.time()) + timedelta(seconds=total_seconds)
    return local_time.replace(tzinfo=timezone.utc) + timedelta(hours=tz_offset)


# ------------------------------------------------------
# Main Prayer Times Calculation
# ------------------------------------------------------

def prayer_times(latitude, longitude, date, calculation_parameters, timezone_offset=0):
    """Reproduces adhanpy 1.0.x calculation logic."""
    method_params = calculation_parameters
    fajr_angle = method_params.get("fajr_angle", 15)
    isha_angle = method_params.get("isha_angle", 15)
    maghrib_angle = method_params.get("maghrib_angle", None)
    isha_interval = method_params.get("isha_interval", None)

    jd = _julian(date)
    decl = _sun_position(jd)

    # Approximate times
    D = decl
    noon = 12 - longitude / 15
    sunrise = _sun_angle_time(-0.833, latitude, D, True)
    sunset = _sun_angle_time(-0.833, latitude, D, False)
    fajr = _sun_angle_time(-fajr_angle, latitude, D, True)
    isha = _sun_angle_time(-isha_angle, latitude, D, False) if isha_interval is None else sunset + (isha_interval / 60)
    maghrib = sunset + 0.0333 if maghrib_angle is None else _sun_angle_time(-maghrib_angle, latitude, D, False)
    dhuhr = noon
    asr_factor = 1 if method_params.get("asr_method") == AsrMethod.STANDARD else 2
    asr = _asr_time(latitude, D, asr_factor)

    # Convert hours to datetime
    times = {
        "fajr": _hours_to_time(fajr, date, timezone_offset),
        "sunrise": _hours_to_time(sunrise, date, timezone_offset),
        "dhuhr": _hours_to_time(dhuhr, date, timezone_offset),
        "asr": _hours_to_time(asr, date, timezone_offset),
        "maghrib": _hours_to_time(maghrib, date, timezone_offset),
        "isha": _hours_to_time(isha, date, timezone_offset)
    }

    return type("PrayerTimes", (), times)()


def _asr_time(lat, decl, factor):
    """Computes the time for Asr."""
    lat_rad = math.radians(lat)
    decl_rad = math.radians(decl)
    val = math.degrees(math.acos((math.sin(math.atan(1 / (factor + math.tan(abs(lat_rad - decl_rad))))) - math.sin(lat_rad) * math.sin(decl_rad)) / (math.cos(lat_rad) * math.cos(decl_rad))))
    return 12 + val / 15.0


# ------------------------------------------------------
# Qibla Direction Calculation
# ------------------------------------------------------

def get_qibla_direction(latitude, longitude):
    """Returns Qibla direction in degrees from true north."""
    kaaba_lat, kaaba_lon = math.radians(21.4225), math.radians(39.8262)
    lat_r = math.radians(latitude)
    lon_r = math.radians(longitude)
    direction = math.degrees(math.atan2(
        math.sin(kaaba_lon - lon_r),
        math.cos(lat_r) * math.tan(kaaba_lat) - math.sin(lat_r) * math.cos(kaaba_lon - lon_r)
    ))
    return (direction + 360) % 360