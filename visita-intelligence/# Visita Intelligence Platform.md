\# 🧠 Visita Intelligence Platform

\#\#\# Unified Data Infrastructure for AI, Automation, and Intelligence Services

\---

\#\# 🌍 Overview

\*\*Visita Intelligence\*\* is the data backbone of the Visita ecosystem — connecting:

\- \*\*Visita AI & Automation\*\* – intelligent automation, dashboards, and data services    
\- \*\*Visita Business\*\* – analytics and insights for business clients    
\- \*\*MyWard\*\* – civic and community intelligence    
\- \*\*Newsauce & African Influencer\*\* – creator and influencer intelligence  

This repository defines the \*\*Supabase database schema\*\*, \*\*data ingestion architecture\*\*, and \*\*API interface\*\* that connects all Apify actors and AI pipelines into a single, queryable intelligence API.

\---

\#\# 🧩 Architecture

Apify Pipelines (raw)  
 ├── Topic Trend Aggregator  
 ├── Sentiment Compass  
 ├── Content Blueprint AI  
 ├── Nuclear / Crime / Fighting Intelligence  
 └── Other Domain Actors  
 ↓  
 Content Autopilot (Orchestrator)  
 ↓  
 Supabase (Unified DB \+ API)  
 ↓  
 Frontends (Visita, Newsauce, MyWard)

\- \*\*Apify Actors\*\* \= raw data producers    
\- \*\*Content Autopilot\*\* \= normalization \+ upload to Supabase    
\- \*\*Supabase\*\* \= storage, analysis, and API serving layer    
\- \*\*Frontends\*\* \= dashboards, portals, and business tools  

\---

\#\# ⚙️ Setup Instructions

\#\#\# 1️⃣ Clone the Repository

\`\`\`bash  
git clone https://github.com/visita-intelligence-platform.git  
cd visita-intelligence-platform

---

### **2️⃣ Install Supabase CLI (Optional for Local Development)**

If you want to run Supabase locally for testing:

npm install supabase \--global  
supabase start

---

### **3️⃣ Environment Variables**

Create a `.env` file at the root of the repository.

SUPABASE\_URL=https://your-project.supabase.co  
SUPABASE\_ANON\_KEY=your-anon-key  
SUPABASE\_SERVICE\_ROLE\_KEY=your-service-role-key  
OPENAI\_API\_KEY=your-openai-key  
APIFY\_TOKEN=your-apify-token

**Note:**

* `SUPABASE_ANON_KEY` → Used by public dashboards and frontends (read-only)

* `SUPABASE_SERVICE_ROLE_KEY` → Used by Content Autopilot (full access)

* `APIFY_TOKEN` → Access to all actor datasets

* `OPENAI_API_KEY` → Required for LLM analysis (Blueprint AI, Trend Aggregator)

---

### **4️⃣ Project Structure**

📦 visita-intelligence-platform  
│  
├── 🧠 database/  
│   ├── schema.sql               \# All Supabase tables and schema definitions  
│   ├── policies.sql             \# RLS policies and role-based access  
│   ├── indexes.sql              \# Indexing for faster trend queries  
│  
├── ⚙️ autopilot/  
│   ├── main.py                  \# Content Autopilot script  
│   ├── input\_schema.json        \# Apify input configuration  
│   ├── dataset\_schema.json      \# Apify output structure  
│  
├── 🔍 actors/  
│   ├── topic\_trend\_aggregator/  \# Raw data aggregator actor  
│   ├── sentiment\_compass/       \# Sentiment analyzer actor  
│   ├── content\_blueprint\_ai/    \# AI insight generator  
│  
├── 📜 docs/  
│   ├── VISITA\_DB\_STRUCTURE.md   \# Full DB \+ API documentation (this file)  
│   └── README.md                \# Setup instructions (you’re reading it)  
│  
└── .env.example

---

## **🗄️ Database Connection**

You can connect using the **Supabase Python Client**, **JS SDK**, or **PostgREST API** directly.

### **Example (Python)**

from supabase import create\_client  
import os

url \= os.getenv("SUPABASE\_URL")  
key \= os.getenv("SUPABASE\_SERVICE\_ROLE\_KEY")

supabase \= create\_client(url, key)

data \= supabase.table("intelligence.trends").select("\*").limit(5).execute()  
print(data)

### **Example (JavaScript)**

import { createClient } from "@supabase/supabase-js"

const supabase \= createClient(import.meta.env.SUPABASE\_URL, import.meta.env.SUPABASE\_ANON\_KEY)

const { data, error } \= await supabase  
  .from("intelligence.trends")  
  .select("cluster\_topic, internal\_trend\_score")  
  .order("internal\_trend\_score", { ascending: false })  
  .limit(10)

console.log(data)

---

## **🧠 Data Flow**

### **🩸 Input (Producers)**

All Apify actors produce datasets (JSON output) under `byseitz.agency` namespace:

* `health-fitness-intelligence`

* `cybersecurity-ai-intelligence`

* `world-news-intelligence`

* etc.

These are **not** sent directly to Supabase.

### **⚙️ Processing**

The **Content Autopilot** actor:

* Pulls datasets from Apify

* Validates and standardizes JSON structures

* Routes data into `intelligence` schema via Supabase REST API (using `service_role`)

### **🧱 Storage**

Supabase stores:

* Trends → `intelligence.trends`

* Sentiment → `intelligence.sentiment`

* Insights → `intelligence.insights`

* Content → `intelligence.content_assets`

* Reports → `reports.intelligence_reports`, `reports.business_reports`

* Crime Data → `crime_intelligence.*`

### **📡 Output (Consumers)**

* **Visita Business Dashboard** → queries intelligence tables via anon key

* **MyWard Civic Panel** → queries `crime_intelligence`

* **Newsauce Creator Panel** → queries `intelligence.content_assets`

* **AI & Automation** → pulls insights from Supabase → visual dashboards

---

## **🔐 Access Layers**

| Access Layer | Use Case | Key | Permissions |
| ----- | ----- | ----- | ----- |
| **Private API** | Data ingestion (Content Autopilot) | `service_role` | Full read/write |
| **Public API** | Dashboards & apps | `anon` | Read-only |
| **Edge Functions** | Composite endpoints | Scoped key | Aggregated responses |

---

## **🧱 REST API Usage**

### **Base URL**

https://\<your-project\>.supabase.co/rest/v1/

### **Required Headers**

apikey: \<SUPABASE\_KEY\>  
Authorization: Bearer \<SUPABASE\_KEY\>  
Content-Type: application/json

---

### **Insert Data (Private API)**

curl \-X POST "https://\<project\>.supabase.co/rest/v1/intelligence.trends" \\  
  \-H "apikey: $SUPABASE\_SERVICE\_ROLE\_KEY" \\  
  \-H "Authorization: Bearer $SUPABASE\_SERVICE\_ROLE\_KEY" \\  
  \-H "Content-Type: application/json" \\  
  \-d '{  
    "domain\_id": "uuid",  
    "cluster\_id": "TREND\_AI\_001",  
    "cluster\_topic": "AI in Healthcare",  
    "internal\_trend\_score": 87.4,  
    "sentiment\_label": "Positive",  
    "articles\_count": 17  
  }'

---

### **Fetch Data (Public API)**

curl \-X GET "https://\<project\>.supabase.co/rest/v1/intelligence.trends?select=cluster\_topic,internal\_trend\_score,sentiment\_label\&order=internal\_trend\_score.desc\&limit=10" \\  
  \-H "apikey: $SUPABASE\_ANON\_KEY" \\  
  \-H "Authorization: Bearer $SUPABASE\_ANON\_KEY"

---

## **🧩 Row-Level Security (RLS)**

Enable RLS for all tables and apply these baseline policies:

\-- Public Read Access  
ALTER TABLE intelligence.trends ENABLE ROW LEVEL SECURITY;  
CREATE POLICY "Public read for trends" ON intelligence.trends FOR SELECT USING (TRUE);

\-- Restricted Writes  
CREATE POLICY "Internal service writes"  
ON intelligence.trends  
FOR INSERT  
USING (auth.role() \= 'service\_role');

---

## **🧱 Index Optimization**

CREATE INDEX IF NOT EXISTS idx\_trends\_domain\_score ON intelligence.trends(domain\_id, internal\_trend\_score DESC);  
CREATE INDEX IF NOT EXISTS idx\_trends\_cluster\_id ON intelligence.trends(cluster\_id);  
CREATE INDEX IF NOT EXISTS idx\_trends\_mentioned\_people\_gin ON intelligence.trends USING GIN(mentioned\_people);

---

## **🧠 Testing the Setup**

Run this after deploying the schema to confirm connection and structure:

curl \-X GET "https://\<project\>.supabase.co/rest/v1/intelligence.trends?limit=1" \\  
  \-H "apikey: $SUPABASE\_ANON\_KEY" \\  
  \-H "Authorization: Bearer $SUPABASE\_ANON\_KEY"

If successful, you should receive a JSON object representing a trend record.

---

## **🚀 Future Expansion Roadmap**

| Phase | Focus | Deliverable |
| ----- | ----- | ----- |
| 1️⃣ | Core integration | Connect Content Autopilot → Supabase |
| 2️⃣ | Public dashboards | Build MyWard & Visita Business visual dashboards |
| 3️⃣ | Edge Functions | Custom aggregated API endpoints |
| 4️⃣ | B2B Data Access | Partner API monetization layer |
| 5️⃣ | Realtime Updates | Add Supabase Realtime for live dashboards |

---

## **👥 Team Notes**

* Keep all Supabase tables, RLS, and policies under `/database/` for version control.

* Always use **Service Role key** in backend automations (never expose it in client apps).

* Use **Apify dataset names** and timestamps as unique dataset identifiers in the `raw_data` schema.

* To add new intelligence domains, insert a record in `intelligence.domains`.

---

## **🪶 Credits**

**Developed by:**  
 🧠 **Visita Intelligence Team**  
 🌍 [visita.co.za](https://visita.co.za)

**Core Maintainer:**  
 [@byseitz.agency](https://apify.com/byseitz.agency)

---

\---

Would you like me to generate a \*\*matching \`/database/schema.sql\`\*\* file next — that automatically creates all the tables, schemas, and relationships described in both the docs and this README?    
That file can be pasted directly into the \*\*Supabase SQL Editor\*\* or version-controlled in your repo.

