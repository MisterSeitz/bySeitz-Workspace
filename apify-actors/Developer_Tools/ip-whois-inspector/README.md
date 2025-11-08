# 🕵️‍♂️ IP WHOIS & Inspector

A fast, all-in-one tool to perform **WHOIS**, **Reverse DNS**, **Geolocation**, and **Port Scanning** for a list of IP addresses.
It finds the **ISP**, **network owner**, **hostname**, **geographic location**, and **open ports** for any public IPv4 or IPv6 address.

---

## ✨ Features

* **Batch Processing:** Process a whole list of IP addresses in a single run.
* **WHOIS/RDAP:** Uses RDAP (Registration Data Access Protocol) for detailed ISP, network, and ASN data.
* **Reverse DNS (PTR):** Finds the associated hostname for an IP address (e.g., `8.8.8.8 → dns.google`).
* **Geolocation:** Pinpoints the IP’s physical location, including country, city, and timezone.
* **Port Scan:** Checks a custom list of common ports (e.g., `80`, `443`, `22`) to see if they are open.

---

## 📥 Input

The Actor's input has been expanded with new options for the added features.

| Field                       | Emoji | Description                                                                                                 |
| --------------------------- | ----- | ----------------------------------------------------------------------------------------------------------- |
| **IP Addresses to Look Up** | 🌐    | A list of IPv4 or IPv6 addresses to inspect (e.g., `8.8.8.8`, `1.1.1.1`).                                   |
| **Perform Reverse DNS**     | 🏷️   | If checked, finds the hostname (PTR record) for each IP.                                                    |
| **Perform Geolocation**     | 🌍    | If checked, finds the physical location (country, city) for each IP.                                        |
| **Perform Port Scan**       | 🚦    | If checked, scans the ports listed in the “Ports to Scan” input field.                                      |
| **Ports to Scan**           | 🔌    | A list of port numbers to check (e.g., `80`, `443`, `22`, `21`, `3306`). Only used if Port Scan is enabled. |

---

## 📤 Output

The Actor saves its results as one item per IP in the Actor's default dataset.

### Example Output

```json
[
  {
    "ip": "8.8.8.8",
    "whois_data": {
      "asn_registry": "arin",
      "asn": "15169",
      "asn_country_code": "US",
      "network": {
        "cidr": "8.8.8.0/24",
        "name": "GOGL",
        "country": "US",
        "entities": ["GOGL"]
      },
      "objects": {
        "GOGL": {
          "handle": "GOGL",
          "name": "Google LLC",
          "contact": {
            "address": [
              {
                "value": "1600 Amphitheatre Parkway\nMountain View\nCA\n94043\nUnited States"
              }
            ],
            "email": [
              { "value": "network-abuse@google.com" }
            ]
          }
        }
      }
    },
    "reverse_dns": {
      "hostname": "dns.google"
    },
    "geolocation": {
      "country": "US",
      "continent": "NA",
      "timezone": "America/Los_Angeles",
      "subdivisions": ["CA"]
    },
    "open_ports": [80, 443]
  }
]
```

---

## 💸 Monetization

This Actor uses the **Pay-Per-Event (PPE)** model.
You will be charged for the following events:

| Event                  | Description                                                                             |
| ---------------------- | --------------------------------------------------------------------------------------- |
| **run_started**        | A small, one-time fee for initiating the Actor run.                                     |
| **ip_processed**       | Charged for each IP address successfully processed (this includes the WHOIS lookup).    |
| **reverse_dns_lookup** | An additional fee charged for each IP when the *Perform Reverse DNS* option is enabled. |
| **geolocation_lookup** | An additional fee charged for each IP when the *Perform Geolocation* option is enabled. |
| **port_scan**          | An additional fee charged for each IP when the *Perform Port Scan* option is enabled.   |

---