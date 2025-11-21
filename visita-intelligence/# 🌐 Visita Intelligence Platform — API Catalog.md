\# 🌐 Visita Intelligence Platform — API Catalog

\> \*\*Last Updated:\*\* November 2025    
\> \*\*Version:\*\* 1.0.0    
\> \*\*Base URL:\*\* \`https://\<PROJECT\>.supabase.co/rest/v1/\`    
\> \*\*Authorization:\*\* All endpoints use Supabase’s RESTful PostgREST API

\---

\#\# 🔑 Authentication

\#\#\# API Keys

| Key | Usage | Access |  
|-----|--------|--------|  
| \`SUPABASE\_ANON\_KEY\` | Used by public clients (web, dashboard) | Read-only |  
| \`SUPABASE\_SERVICE\_ROLE\_KEY\` | Used by backend services (Apify → Autopilot) | Full read/write |

\#\#\# Headers

\`\`\`bash  
\-H "apikey: \<API\_KEY\>"  
\-H "Authorization: Bearer \<API\_KEY\>"  
\-H "Content-Type: application/json"

---

## **📦 Schema: `intelligence`**

The **Intelligence Schema** stores AI-processed trend, sentiment, and insights data.

---

### **GET `/intelligence.trends`**

Fetch all trend clusters detected by the Topic Trend Aggregator.

#### **Example**

curl "https://\<PROJECT\>.supabase.co/rest/v1/intelligence.trends?limit=10" \\  
  \-H "apikey: \<SUPABASE\_ANON\_KEY\>" \\  
  \-H "Authorization: Bearer \<SUPABASE\_ANON\_KEY\>"

#### **Parameters**

| Param | Type | Example | Description |
| ----- | ----- | ----- | ----- |
| `cluster_topic` | `eq`, `ilike`, etc. | `cluster_topic=ilike.*AI*` | Filter by keyword in topic |
| `sentiment_label` | `eq` | `sentiment_label=eq.Positive` | Filter by sentiment |
| `order` | `string` | `order=internal_trend_score.desc` | Sort by trend strength |
| `limit` | `int` | `limit=10` | Limit results |

#### **Access**

* ✅ **Public:** Read

* 🔒 **Private (Service Role):** Insert, Update, Delete

---

### **POST `/intelligence.trends`**

Insert or update trends from **Content Autopilot**.

curl \-X POST "https://\<PROJECT\>.supabase.co/rest/v1/intelligence.trends" \\  
  \-H "apikey: \<SUPABASE\_SERVICE\_ROLE\_KEY\>" \\  
  \-H "Authorization: Bearer \<SUPABASE\_SERVICE\_ROLE\_KEY\>" \\  
  \-H "Content-Type: application/json" \\  
  \-d '{  
    "cluster\_topic": "AI in Education",  
    "internal\_trend\_score": 92.1,  
    "sentiment\_label": "Positive",  
    "articles\_count": 14  
  }'

---

### **GET `/intelligence.sentiment`**

Retrieve summarized sentiment analytics from Sentiment Compass.

| Parameter | Example | Description |
| ----- | ----- | ----- |
| `sentiment_label` | `eq.Positive` | Filter by sentiment |
| `order` | `sentiment_score.desc` | Sort by sentiment score |

#### **Example:**

curl "https://\<PROJECT\>.supabase.co/rest/v1/intelligence.sentiment?order=sentiment\_score.desc\&limit=5" \\  
  \-H "apikey: \<SUPABASE\_ANON\_KEY\>"

---

### **GET `/intelligence.insights`**

Returns human-readable summaries and observations from the AI pipeline.

| Param | Example | Description |
| ----- | ----- | ----- |
| `category` | `eq.Health` | Filter by domain |
| `order` | `created_at.desc` | Sort newest first |

---

### **GET `/intelligence.content_assets`**

Returns generated articles, scripts, and multimedia summaries for platforms like Newsauce.

| Param | Example | Description |
| ----- | ----- | ----- |
| `asset_type` | `eq.Script` | Filter by asset type |
| `category` | `eq.RealEstate` | Filter by topic |
| `order` | `created_at.desc` | Sort by newest |

#### **Example:**

curl "https://\<PROJECT\>.supabase.co/rest/v1/intelligence.content\_assets?category=eq.RealEstate\&limit=3" \\  
  \-H "apikey: \<SUPABASE\_ANON\_KEY\>"

---

### **GET `/intelligence.domains`**

Internal lookup table for registered data domains (e.g., Nuclear Intelligence, Retail, etc.).

🔒 **Access:** Service Role only  
 ✅ **Used by:** Content Autopilot, internal analysis scripts.

---

## **🧠 Schema: `crime_intelligence`**

Used by **Visita MyWard** for civic and public safety intelligence.

---

### **GET `/crime_intelligence.missing_people`**

Fetch current missing persons data.

| Param | Example | Description |
| ----- | ----- | ----- |
| `name` | `ilike.*John*` | Search by name |
| `location` | `ilike.*Durban*` | Filter by region |
| `order` | `date_missing.desc` | Sort by date |

#### **Example**

curl "https://\<PROJECT\>.supabase.co/rest/v1/crime\_intelligence.missing\_people?order=date\_missing.desc" \\  
  \-H "apikey: \<SUPABASE\_ANON\_KEY\>"

---

### **GET `/crime_intelligence.wanted_people`**

Fetch public wanted suspects database.

| Param | Example | Description |
| ----- | ----- | ----- |
| `name` | `ilike.*Smith*` | Search by name |
| `crime` | `ilike.*fraud*` | Filter by crime type |
| `order` | `created_at.desc` | Sort by newest entries |

---

### **GET `/crime_intelligence.structured_crime_intelligence`**

Aggregated and AI-enriched reports on crime and safety incidents.

| Param | Example | Description |
| ----- | ----- | ----- |
| `incident_type` | `eq.Homicide` | Filter by incident type |
| `severity` | `eq.High` | Filter by severity |
| `order` | `incident_date.desc` | Sort by recency |

---

### **GET `/crime_intelligence.crime_reports`**

Public or analytical summary of civic safety data.

| Param | Example | Description |
| ----- | ----- | ----- |
| `location` | `ilike.*Cape Town*` | Filter by city |
| `incident_type` | `eq.Robbery` | Filter by type |
| `order` | `incident_date.desc` | Sort by date |

---

## **📑 Schema: `reports`**

Used for all auto-generated and human-curated reports across Visita’s verticals.

---

### **GET `/reports.intelligence_reports`**

AI-generated market and domain reports from the Intelligence schema.

| Param | Example | Description |
| ----- | ----- | ----- |
| `category` | `eq.AI` | Filter by category |
| `order` | `created_at.desc` | Sort by date |

---

### **GET `/reports.business_reports`**

Business and market intelligence reports for Visita Business subscribers.

| Param | Example | Description |
| ----- | ----- | ----- |
| `industry` | `eq.Retail` | Filter by business sector |
| `order` | `created_at.desc` | Sort by latest |

---

### **GET `/reports.civic_reports`**

Civic transparency and ward-based performance data.

| Param | Example | Description |
| ----- | ----- | ----- |
| `ward_id` | `eq.23` | Filter by ward number |
| `order` | `created_at.desc` | Sort by newest |

---

## **🧩 Standard Query Operators**

Supabase REST API supports PostgreSQL-style operators for filtering.

| Operator | Meaning | Example |
| ----- | ----- | ----- |
| `eq` | Equals | `?city=eq.Cape Town` |
| `neq` | Not equals | `?severity=neq.High` |
| `gt` | Greater than | `?score=gt.50` |
| `lt` | Less than | `?articles_count=lt.5` |
| `ilike` | Case-insensitive LIKE | `?title=ilike.*Energy*` |
| `in` | In array | `?category=in.(AI,Health,Finance)` |
| `is` | NULL check | `?summary=is.null` |
| `order` | Sort results | `?order=created_at.desc` |
| `limit` | Limit number of records | `?limit=10` |
| `offset` | Pagination offset | `?offset=20` |

---

## **🛡️ Access Summary by Role**

| Schema | Public (anon) | Authenticated | Service Role |
| ----- | ----- | ----- | ----- |
| intelligence | ✅ Read | ✅ Read | ✅ Read/Write/Delete |
| crime\_intelligence | ✅ Read | ✅ Read | ✅ Read/Write/Delete |
| reports | ✅ Read | ✅ Read | ✅ Read/Write/Delete |
| public | ✅ Read | ✅ Read | ✅ Read |
| internal (domains) | ❌ None | ❌ None | ✅ Full |

---

## **📈 API Rate Limits**

| Role | Limit | Notes |
| ----- | ----- | ----- |
| Public (anon) | 60 requests/min | Cached for dashboards |
| Authenticated | 300 requests/min | For future OAuth users |
| Service Role | Unlimited | Used internally via secure environment variables |

---

## **⚙️ Versioning & Maintenance**

* **API Version:** `v1` (PostgREST default)

* **Schema Migration:** Managed in `/database/migrations`

* **Docs:** This file (`api_catalog.md`) updated whenever a new table is added.

---

## **🧭 Next Steps**

| Goal | Description |
| ----- | ----- |
| Add `nuclear_intelligence` schema | Tracks nuclear industry data, tied to government initiatives |
| Add `fighting_intelligence` schema | Tracks UFC, MMA, and other fight industry metrics |
| Add `/v2/graphql` endpoint | Planned for multi-source joins (e.g., domain \+ trends \+ sentiment) |
| Add webhook listeners | To trigger updates in MyWard or Newsauce dashboards |

---

**Maintained by:**  
 Visita Systems — Intelligence, AI & Data Infrastructure  
 📧 support@visita.co.za | 🌐 [https://visita.co.za](https://visita.co.za)

