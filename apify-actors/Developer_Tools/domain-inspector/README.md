# 🕵️‍♂️ Domain Inspector

A powerful, all-in-one tool to perform **DNS lookups**, **WHOIS queries**, **HTTP status checks**, and **SSL certificate validation** for a list of domains.

It can clean full URLs down to the bare domain
(e.g., `https://www.apify.com/store` → `apify.com`)
and run all checks in a single batch.

---

## ✨ Features

* **Batch Processing:** Process a whole list of domains in a single run.
* **Smart URL Cleaning:** Automatically extracts the correct domain (`apify.com`) from full URLs (`https://www.apify.com/store?q=new`).
* **Custom DNS Lookups:** Choose exactly which DNS records to query (`A`, `AAAA`, `MX`, `TXT`, `CNAME`, `NS`, `SOA`).
* **WHOIS Data:** Optionally performs a WHOIS lookup to get registrar, creation, and expiration dates.
* **HTTP Status:** Optionally checks the `http://` and `https://` versions of the domain to get their HTTP status code (e.g., `200`, `301`, `404`).
* **SSL Certificate:** Optionally checks the SSL certificate to find the issuer and expiration date.

---

## 📥 Input

The Actor's input is defined by the `.actor/input_schema.json` file.

| Field                             | Emoji | Description                                                                                               |
| --------------------------------- | ----- | --------------------------------------------------------------------------------------------------------- |
| **Domains to Look Up**            | 🌐    | A list of domains or full URLs to inspect. The tool will automatically clean them.                        |
| **Record Types to Query**         | 🔍    | A multi-select dropdown to choose which DNS record types to query.                                        |
| **Perform WHOIS Lookup**          | 👤    | A checkbox. If checked, the Actor will perform a WHOIS query for each domain.                             |
| **Perform HTTP Status Check**     | 🚦    | A checkbox. If checked, the Actor will check the HTTP status code for `http://` and `https://` protocols. |
| **Perform SSL Certificate Check** | 🔒    | A checkbox. If checked, the Actor will check the SSL certificate for its issuer and expiration date.      |

---

## 📤 Output

The Actor saves its results as one item per domain in the Actor's default dataset.

### Example Output

```json
[
  {
    "domain": "apify.com",
    "records": {
      "A": ["104.18.23.133", "104.18.22.133"],
      "MX": [
        { "preference": 1, "exchange": "aspmx.l.google.com." }
      ],
      "TXT": ["google-site-verification=..."],
      "NS": ["ns-1032.awsdns-01.org."],
      "SOA": [
        {
          "mname": "ns-1032.awsdns-01.org.",
          "rname": "awsdns-hostmaster.amazon.com.",
          "serial": 1,
          "refresh": 7200,
          "retry": 900,
          "expire": 1209600,
          "minimum": 86400
        }
      ]
    },
    "whois": {
      "domain_name": ["APIFY.COM", "apify.com"],
      "registrar": "Amazon Registrar, Inc.",
      "creation_date": "2015-02-12T15:35:14+00:00",
      "expiration_date": "2027-02-12T15:35:14+00:00",
      "emails": [
        "abuse@amazonaws.com",
        "proxy-contact@registrar.amazon.com"
      ]
    },
    "http_status": {
      "https": { "status_code": 200, "url": "https://apify.com" },
      "http": { "status_code": 301, "url": "http://apify.com" }
    },
    "ssl_info": {
      "issuer": "GTS CA 1P5",
      "expires": "2025-12-15T08:50:39+00:00",
      "error": null
    }
  }
]
```

---

## 💸 Monetization

This Actor uses the **Pay-Per-Event (PPE)** model.
You will be charged for the following events:

| Event                | Description                                                                                           |
| -------------------- | ----------------------------------------------------------------------------------------------------- |
| **run_started**      | A small, one-time fee for initiating the Actor run.                                                   |
| **domain_processed** | Charged for each domain successfully processed from your input list.                                  |
| **whois_lookup**     | An additional fee charged for each domain when the *Perform WHOIS Lookup* option is enabled.          |
| **http_check**       | An additional fee charged for each domain when the *Perform HTTP Status Check* option is enabled.     |
| **ssl_check**        | An additional fee charged for each domain when the *Perform SSL Certificate Check* option is enabled. |

> ⚠️ **Note:**
> The default `apify-default-dataset-item` event (for saving results) is disabled to avoid double-charging you for results.