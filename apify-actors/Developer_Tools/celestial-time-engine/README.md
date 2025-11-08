# 🌌 Celestial Time Engine — Multi-Faith Astronomical & Prayer Time Calculator

The **Celestial Time Engine v2** is an **all-in-one astronomical and religious time calculator** built for automation on [Apify](https://apify.com).
It calculates **sunrise, sunset, twilight phases, prayer times, Qibla direction, moon phases, weather data**, and more — for any location on Earth.

Provide **place names, coordinates, or presets** (e.g., 🕋 Mecca, 🇿🇦 Cape Town, 🇹🇷 Istanbul) and receive a detailed dataset of celestial and faith-based time events.

---

## ✨ What Celestial Time Engine can do

**Main features**

* ☀️ **Core Sun Module** — sunrise, sunset, solar noon and midnight, day length.
* ✈️ **Aviation Twilight** — civil, nautical and astronomical dawn and dusk.
* 🕌 **Islamic Prayer Times** — Fajr to Isha, Asr methods, and Qibla direction.
* 📸 **Photography Hours** — golden and blue hour start and end times.
* 🌙 **Moon Phases and Rise/Set** — phase name, illumination, rise, and set.
* 🌤️ **Weather Layer** — live conditions and cloud cover (via OpenWeatherMap API).
* ✡️ **Jewish Zmanim** — Alot HaShachar and Tzeit HaKochavim.
* 🧭 **Magnetic Declination** — calculate magnetic north offset (geomagnetic model).
* 🕉️ **Lunar Calendars** — Chinese and Hindu day data (optional).

**Highlights**

* Process **multiple locations at once** (batch input).
* Smart geocoding with automatic timezone detection.
* Works for any date — past or future.
* Outputs are **standard ISO timestamps**, ideal for data pipelines or CSV exports.

---

## 🌍 Why use Celestial Time Engine v2 on Apify?

Running the Engine on Apify gives you:

* **Automation & Scheduling** — calculate times daily or hourly.
* **API Access** — integrate directly with apps and dashboards.
* **Proxy & Network Tools** — ensure geolocation accuracy.
* **Scalable Batch Processing** — thousands of locations per run.
* **Integrated Storage** — save and export datasets in JSON, CSV, or Excel.

Unlike local apps, Apify Actors run entirely in the cloud and scale automatically.

---

## 📥 Input options

You can see all inputs under the **Input tab** in Apify Console.

| Field                   | Type               | Description                                                                                                       |
| ----------------------- | ------------------ | ----------------------------------------------------------------------------------------------------------------- |
| `locations`             | array              | A list of places or coordinates (e.g. `"Cape Town, South Africa"` or `{ "latitude": 21.42, "longitude": 39.82 }`) |
| `date`                  | string             | Date in `YYYY-MM-DD` format (defaults to today).                                                                  |
| `modules`               | array              | Which modules to calculate (`core`, `islamic`, `moon`, `weather`, etc.).                                          |
| `config.islamic.method` | string             | Calculation method (ISNA, Makkah, Turkey, Dubai, etc.).                                                           |
| `config.islamic.asr`    | string             | Asr method (Standard or Hanafi).                                                                                  |
| `weatherApiKey`         | string 🔒 (secret) | Your OpenWeatherMap API key (if Weather module is enabled).                                                       |
| `flattenOutput`         | boolean            | Flatten output for easy CSV import.                                                                               |

---

### 🧭 Preset locations

Quickly select from popular places:

| Preset         | Example                 |
| -------------- | ----------------------- |
| 🇸🇦 Mecca     | `"preset": "mecca"`     |
| 🇿🇦 Cape Town | `"preset": "cape_town"` |
| 🇹🇷 Istanbul  | `"preset": "istanbul"`  |
| 🇪🇬 Cairo     | `"preset": "cairo"`     |
| 🇦🇪 Dubai     | `"preset": "dubai"`     |

---

## 📤 Output example

Each location is saved as one item in the Actor’s default dataset.

```json
{
  "resolved": {
    "name": "Cape Town, South Africa",
    "latitude": -33.9249,
    "longitude": 18.4241
  },
  "date": "2025-11-07",
  "timezone": "Africa/Johannesburg",
  "modules": {
    "core_sun": {
      "sunrise": "2025-11-07T05:23:41+02:00",
      "sunset": "2025-11-07T19:31:12+02:00",
      "day_length_seconds": 50951
    },
    "islamic_prayer": {
      "fajr": "2025-11-07T04:21:00+02:00",
      "dhuhr": "2025-11-07T12:08:00+02:00",
      "asr": "2025-11-07T15:24:00+02:00",
      "maghrib": "2025-11-07T19:31:00+02:00",
      "isha": "2025-11-07T20:47:00+02:00",
      "qibla_direction_degrees": 21.38
    },
    "moon": {
      "phase_name": "Waxing Crescent",
      "illumination_percent": 23.4
    },
    "weather": {
      "conditions": "clear sky",
      "temp_c": 23.8,
      "cloud_cover_percent": 0
    }
  }
}
```

All datasets can be downloaded as **JSON, CSV, HTML, or Excel** from the dataset tab.

---

## 🧩 How to use Celestial Time Engine v2

1. Open the Actor in [Apify Console](https://console.apify.com/).
2. Click **Run** → **Input**.
3. Enter a list of locations or choose presets.
4. (Optional) Add your OpenWeatherMap API key to enable weather data.
5. Select modules you want (e.g. `core`, `islamic`, `moon`).
6. Click **Run** and watch the dataset populate in real time.

---

## 💰 Pricing and usage expectations

This Actor uses Apify’s **pay-per-compute-unit (PPU)** model.
You pay only for the resources used during your run – no fixed fee.

* Typical single-location run ≈ 0.01 CU (less than $0.001).
* Multi-location batch (100 entries) ≈ 1 CU.
* Includes all calculations and geocoding.

You can start for **free** on Apify’s starter plan and scale as needed.

---

## ⚙️ Advanced configuration

| Module                   | Options                                                                  |
| ------------------------ | ------------------------------------------------------------------------ |
| **Islamic Prayer Times** | Method (ISNA, Makkah, Turkey, Dubai, etc.), Asr Method (Standard/Hanafi) |
| **Weather**              | Requires OpenWeatherMap API Key                                          |
| **Output**               | Toggle `flattenOutput` to make dataset spreadsheet-friendly              |
| **Batch Processing**     | Input multiple locations in one run                                      |

---

## 💡 Tips for best results

* Keep location names precise (e.g., “Mecca, Saudi Arabia”).
* For the Weather module, use metric data (`units=metric`).
* Schedule daily runs to automatically generate prayer timetables.
* Combine this Actor with [Apify Webhooks](https://docs.apify.com/platform/integrations/webhooks) to send notifications at Fajr or Sunset.

---

## 🧾 FAQ and support

### Is Celestial Time Engine v2 accurate?

Yes — it uses Astral and verified astronomical equations for the sun, plus standard ISNA/Makkah angles for prayers.

### Is it free to use?

You can run small batches for free under Apify’s free plan.

### Can I add my own API keys or custom angles?

Yes — you can extend the JSON config object in the input schema.

### Where to get help?

If you face issues or want custom features (e.g., holiday calendar integration), open an issue in Apify Console or contact support.

---

## 🚀 Integrations and use cases

* Generate daily Islamic prayer times for apps or IoT devices.
* Automate photography schedules based on golden hour.
* Sync moon phase data to lighting systems or agriculture tools.
* Export CSV timetables for religious websites or community boards.

---

**Start now** → [Run Celestial Time Engine v2 on Apify](https://console.apify.com/)
and get precise sun, moon, and prayer data for any place on Earth ☀️🌙🕌