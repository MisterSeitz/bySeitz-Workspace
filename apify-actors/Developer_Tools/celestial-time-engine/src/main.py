"""
main.py — Celestial Time Engine v2
Final version using internal adhan_utils.py for Islamic calculations
and Qibla direction (no external adhanpy dependency).
"""

import asyncio
from datetime import datetime, date as date_obj
from typing import Any, Dict, Optional, List
import collections
import math

from apify import Actor
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable
from timezonefinder import TimezoneFinder
import pytz

# --- Internal Islamic and Qibla logic ---
from src.adhan_utils import prayer_times, CalculationMethod, AsrMethod, get_qibla_direction

# --- Astronomical calculations ---
from astral import Observer
from astral.sun import sun, golden_hour, blue_hour, dawn, dusk, SunDirection

# Optional extras
try:
    from astral import moon as astral_moon
except Exception:
    astral_moon = None

try:
    import requests
except Exception:
    requests = None

try:
    import lunardate
    LUNAR_AVAILABLE = True
except Exception:
    LUNAR_AVAILABLE = False

try:
    import geomag
    GEOMAG_AVAILABLE = True
except Exception:
    geomag = None
    GEOMAG_AVAILABLE = False

# -----------------------
# Preset city coordinates
# -----------------------
PRESET_LOCATIONS = {
    "mecca": {"latitude": 21.4225, "longitude": 39.8262, "query": "Mecca, Saudi Arabia"},
    "medina": {"latitude": 24.4709, "longitude": 39.6122, "query": "Medina, Saudi Arabia"},
    "cape_town": {"latitude": -33.9249, "longitude": 18.4241, "query": "Cape Town, South Africa"},
    "cairo": {"latitude": 30.0444, "longitude": 31.2357, "query": "Cairo, Egypt"},
    "istanbul": {"latitude": 41.0082, "longitude": 28.9784, "query": "Istanbul, Turkey"},
    "dubai": {"latitude": 25.276987, "longitude": 55.296249, "query": "Dubai, UAE"},
    "london": {"latitude": 51.5074, "longitude": -0.1278, "query": "London, UK"},
    "new_york": {"latitude": 40.7128, "longitude": -74.0060, "query": "New York, USA"},
    "jakarta": {"latitude": -6.2088, "longitude": 106.8456, "query": "Jakarta, Indonesia"},
    "lagos": {"latitude": 6.5244, "longitude": 3.3792, "query": "Lagos, Nigeria"}
}


# -----------------------
# Utility functions
# -----------------------
def flatten_dict(d: Dict[str, Any], parent_key: str = "", sep: str = "_") -> Dict[str, Any]:
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, collections.abc.MutableMapping):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


def format_dt(dt: Optional[datetime]) -> Optional[str]:
    return dt.isoformat() if dt else None


def simple_moon_phase(date_obj_local: date_obj) -> Dict[str, Any]:
    known_new_moon = datetime(2000, 1, 6, 18, 14)
    dt = datetime(date_obj_local.year, date_obj_local.month, date_obj_local.day)
    days = (dt - known_new_moon).days + (dt - known_new_moon).seconds / 86400.0
    synodic_month = 29.53058867
    phase = (days % synodic_month) / synodic_month
    illumination = (1 - math.cos(2 * math.pi * phase)) / 2 * 100
    if phase < 0.02 or phase > 0.98:
        name = "New Moon"
    elif phase < 0.25:
        name = "Waxing Crescent"
    elif phase == 0.25:
        name = "First Quarter"
    elif phase < 0.5:
        name = "Waxing Gibbous"
    elif phase == 0.5:
        name = "Full Moon"
    elif phase < 0.75:
        name = "Waning Gibbous"
    elif phase == 0.75:
        name = "Last Quarter"
    else:
        name = "Waning Crescent"
    return {"phase_name": name, "illumination_percent": round(illumination, 2)}


def fetch_weather(lat: float, lon: float, api_key: str) -> Optional[Dict[str, Any]]:
    if not requests:
        Actor.log.warning("requests library not available; skipping weather.")
        return None
    try:
        url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&units=metric&appid={api_key}"
        r = requests.get(url, timeout=8)
        r.raise_for_status()
        data = r.json()
        return {
            "conditions": data.get("weather", [{}])[0].get("description"),
            "temp_c": data.get("main", {}).get("temp"),
            "cloud_cover_percent": data.get("clouds", {}).get("all")
        }
    except Exception as e:
        Actor.log.warning(f"Weather fetch failed: {e}")
        return None


# -----------------------
# Main Actor
# -----------------------
async def main() -> None:
    async with Actor:
        Actor.log.info("🚀 Starting Celestial Time Engine v2...")

        actor_input = await Actor.get_input() or {}
        locations_input: List[Dict[str, Any]] = actor_input.get("locations", [])
        process_date_str: str = actor_input.get("date", datetime.now().strftime("%Y-%m-%d"))
        modules: List[str] = actor_input.get("modules", ["core"])
        config: Dict[str, Any] = actor_input.get("config", {})
        flatten_output: bool = actor_input.get("flattenOutput", False)

        islamic_config: Dict[str, str] = config.get("islamic", {})
        islamic_method: str = islamic_config.get("method", "ISNA")
        islamic_asr: str = islamic_config.get("asr", "STANDARD")

        # Weather API key (top-level, secret in schema)
        weather_api_key: Optional[str] = actor_input.get("weatherApiKey")

        geolocator = Nominatim(user_agent=f"apify-actor/{Actor.configuration.actor_id or 'local-run'}")
        tf = TimezoneFinder()
        process_date: date_obj = datetime.strptime(process_date_str, "%Y-%m-%d").date()

        if not locations_input:
            Actor.log.warning("No locations provided. Using Cape Town as default.")
            locations_input = [{"query": "Cape Town, South Africa"}]

        results: List[Dict[str, Any]] = []

        for loc in locations_input:
            # Handle preset dropdown
            preset = loc.get("preset")
            if preset and preset in PRESET_LOCATIONS:
                loc.update(PRESET_LOCATIONS[preset])

            location_data: Dict[str, Any] = {
                "input": loc,
                "resolved": {},
                "date": process_date_str,
                "timezone": None,
                "modules": {}
            }

            try:
                lat = loc.get("latitude")
                lon = loc.get("longitude")
                query = loc.get("query")
                custom_id = loc.get("customId")
                if custom_id:
                    location_data["customId"] = custom_id

                geocoded_location = None
                display_name = query or f"{lat},{lon}"

                # Resolve missing coordinates
                if lat is None or lon is None:
                    try:
                        geocoded_location = geolocator.geocode(query, timeout=5)
                        if geocoded_location:
                            lat, lon = geocoded_location.latitude, geocoded_location.longitude
                            display_name = geocoded_location.address
                    except Exception as e:
                        Actor.log.warning(f"Geocoding failed for {query}: {e}")
                        continue

                location_data["resolved"] = {"name": display_name, "latitude": lat, "longitude": lon}
                timezone_str = tf.timezone_at(lng=lon, lat=lat)
                if not timezone_str:
                    Actor.log.warning(f"No timezone found for {display_name}.")
                    continue
                timezone_obj = pytz.timezone(timezone_str)
                location_data["timezone"] = timezone_str

                obs = Observer(latitude=lat, longitude=lon)

                # --- Core Sun Module ---
                if "core" in modules:
                    try:
                        s = sun(obs, date=process_date, tzinfo=timezone_obj)
                        location_data["modules"]["core_sun"] = {
                            "sunrise": format_dt(s.get("sunrise")),
                            "sunset": format_dt(s.get("sunset")),
                            "solar_noon": format_dt(s.get("noon")),
                            "solar_midnight": format_dt(s.get("midnight")),
                            "day_length_seconds": (s["sunset"] - s["sunrise"]).total_seconds()
                            if s.get("sunrise") and s.get("sunset") else None
                        }
                    except Exception as e:
                        Actor.log.warning(f"Sun calc failed: {e}")

                # --- Islamic Prayer Times ---
                if "islamic" in modules:
                    try:
                        params = CalculationMethod.get_params(islamic_method)
                        params["asr_method"] = AsrMethod.get_method(islamic_asr)
                        offset_hours = timezone_obj.utcoffset(datetime.combine(process_date, datetime.min.time())).total_seconds() / 3600
                        prayers = prayer_times(lat, lon, process_date, params, offset_hours)
                        qibla = get_qibla_direction(lat, lon)
                        location_data["modules"]["islamic_prayer"] = {
                            "fajr": format_dt(prayers.fajr),
                            "sunrise": format_dt(prayers.sunrise),
                            "dhuhr": format_dt(prayers.dhuhr),
                            "asr": format_dt(prayers.asr),
                            "maghrib": format_dt(prayers.maghrib),
                            "isha": format_dt(prayers.isha),
                            "calculation_method": islamic_method,
                            "asr_method": islamic_asr,
                            "qibla_direction_degrees": qibla
                        }
                    except Exception as e:
                        Actor.log.warning(f"Islamic calc failed: {e}")

                # --- Moon ---
                if "moon" in modules:
                    try:
                        moon_info = simple_moon_phase(process_date)
                        if astral_moon:
                            try:
                                mr = astral_moon.moonrise(obs, date=process_date, tzinfo=timezone_obj)
                                ms = astral_moon.moonset(obs, date=process_date, tzinfo=timezone_obj)
                                moon_info["moonrise"] = format_dt(mr)
                                moon_info["moonset"] = format_dt(ms)
                            except Exception:
                                pass
                        location_data["modules"]["moon"] = moon_info
                    except Exception as e:
                        Actor.log.warning(f"Moon module failed: {e}")

                # --- Weather ---
                if "weather" in modules:
                    try:
                        if weather_api_key:
                            w = fetch_weather(lat, lon, weather_api_key)
                            location_data["modules"]["weather"] = w or {}
                        else:
                            Actor.log.warning("Weather module enabled but no API key set.")
                    except Exception as e:
                        Actor.log.warning(f"Weather failed: {e}")

                # --- Chinese Lunar Calendar ---
                if "chinese" in modules and LUNAR_AVAILABLE:
                    try:
                        lunar = lunardate.LunarDate.fromSolarDate(process_date.year, process_date.month, process_date.day)
                        location_data["modules"]["chinese"] = {
                            "lunar_year": lunar.year,
                            "lunar_month": lunar.month,
                            "lunar_day": lunar.day
                        }
                    except Exception as e:
                        Actor.log.warning(f"Chinese module failed: {e}")

                # --- Magnetic Declination ---
                if "magnetic" in modules and GEOMAG_AVAILABLE:
                    try:
                        decl = geomag.declination(lat, lon)
                        location_data["modules"]["magnetic_declination"] = {"declination_degrees": decl}
                    except Exception as e:
                        Actor.log.warning(f"Magnetic declination failed: {e}")

                results.append(flatten_dict(location_data) if flatten_output else location_data)

            except Exception as e:
                Actor.log.error(f"Error for {loc}: {e}")

        await Actor.push_data(results)
        Actor.log.info("✅ Celestial Time Engine v2 finished.")


if __name__ == "__main__":
    asyncio.run(main())