\# 🧠 Visita Intelligence Platform — Supabase Security Overview

\> \*\*Last Updated:\*\* November 2025    
\> \*\*Author:\*\* Visita Data Systems    
\> \*\*Purpose:\*\* Documentation of Supabase database security, schema access, and data flow.

\---

\#\# 🏗️ Platform Architecture

Visita’s Supabase environment underpins the \*\*Intelligence\*\*, \*\*Business\*\*, and \*\*Civic Ward\*\* ecosystems.    
It serves as the \*\*central structured database\*\* for all AI, automation, and intelligence services.

\#\#\# 🔄 Data Flow Overview

\`\`\`

\[Apify Actors\] → \[Preprocessors\] → \[Content Autopilot\] → \[Supabase\]  
↓                                             ↓  
(Raw \+ Enriched Feeds)                  (Storage \+ Reports \+ API Access)

\`\`\`

\*\*Downstream Clients:\*\*  
\- \*\*Visita AI\*\* → AI & Automation services    
\- \*\*Visita Intelligence\*\* → Aggregated trend, sentiment, and domain insights    
\- \*\*Visita MyWard\*\* → Community, safety, and civic data (crime reports, missing people)    
\- \*\*Visita Business\*\* → Directory \+ Data dashboards for verified businesses    
\- \*\*Newsauce\*\* → Creator-focused analytics and AI-generated scripts    
\- \*\*African Influencer\*\* → Influencer intelligence and affiliate dashboards  

\---

\#\# 🧱 Schemas & Access Model

Each schema in Supabase has \*\*Row Level Security (RLS)\*\* enabled, with strict role-based access.  

\#\#\# 🔐 Roles Defined

| Role | Description | Access Type |  
|------|--------------|-------------|  
| \`anon\` | Default public API role used by client-side apps (e.g., Visita website, dashboards) | \*\*Read-only\*\* |  
| \`authenticated\` | Reserved for user-authenticated apps (future OAuth/API key users) | \*\*Read-only\*\* |  
| \`service\_role\` | Used by internal systems like Content Autopilot and data preprocessors | \*\*Full read/write\*\* |

\---

\#\# 📊 Schema: \`intelligence\`

Stores all data related to \*\*AI-driven insights, topic trends, sentiment analysis, and automation outputs\*\*.

| Table | Purpose | Public Access | Service Role Access | Notes |  
|--------|----------|----------------|----------------------|-------|  
| \`trends\` | Main trend clusters from Topic Trend Aggregator | ✅ Read | ✅ Full (Insert/Update/Delete) | Used for reports & dashboards |  
| \`sentiment\` | Cluster sentiment and emotional analysis | ✅ Read | ✅ Full | Output of Sentiment Compass |  
| \`insights\` | Final summarized insights for dashboards | ✅ Read | ✅ Full | Used for Visita reports |  
| \`content\_assets\` | LLM-generated content (scripts, summaries, visuals) | ✅ Read | ✅ Full | Powers Newsauce and creator tools |  
| \`domains\` | Internal lookup for intelligence domains (e.g., nuclear, health, retail) | ❌ None | ✅ Full | Restricted internal table |  
| \`entries\` | Raw or staged entries from preprocessors | ✅ Read | ✅ Full | For ingestion monitoring |

\---

\#\# 🧩 Schema: \`crime\_intelligence\`

Focuses on \*\*community and safety data\*\* integrated with MyWard.

| Table | Purpose | Public Access | Service Role Access | Notes |  
|--------|----------|----------------|----------------------|-------|  
| \`missing\_people\` | Records of missing individuals from SAPS feeds or reports | ✅ Read | ✅ Full | Updated by scraper \+ citizen reports |  
| \`wanted\_people\` | Data on wanted suspects or fugitives | ✅ Read | ✅ Full | Sourced from SAPS |  
| \`structured\_crime\_intelligence\` | Enriched intelligence from crime datasets | ✅ Read | ✅ Full | Feeds MyWard safety dashboard |  
| \`crime\_reports\` | Generic or aggregated crime statistics | ✅ Read | ✅ Full | Used for analytics and visual dashboards |

\---

\#\# 📑 Schema: \`reports\`

Holds all \*\*intelligence, business, and civic reports\*\* derived from Supabase data.

| Table | Purpose | Public Access | Service Role Access | Notes |  
|--------|----------|----------------|----------------------|-------|  
| \`intelligence\_reports\` | Aggregated AI/trend reports for Visita Intelligence | ✅ Read | ✅ Full | Accessible on business dashboards |  
| \`business\_reports\` | Reports generated for Visita Business subscribers | ✅ Read | ✅ Full | Includes economic, retail & performance insights |  
| \`civic\_reports\` | Public municipal reports and summaries for MyWard | ✅ Read | ✅ Full | Open civic transparency layer |

\---

\#\# 🧩 Schema: \`public\`

Contains default Supabase system metadata, no sensitive data stored here.    
RLS is not used on this schema.

\---

\#\# 🔐 Security Summary

| Type | Access Level | Description |  
|------|---------------|-------------|  
| \*\*Public Dashboards (anon key)\*\* | Read-only | Can view aggregated data and insights only |  
| \*\*Internal Services (service\_role key)\*\* | Full read/write | Used by Apify → Autopilot → Supabase ingestion pipeline |  
| \*\*End Users (future OAuth)\*\* | Scoped | Will receive scoped access to their data (e.g., their business profile) |

\---

\#\# 🚀 API Access Overview

\#\#\# REST API Endpoints

All Supabase tables are accessible through the \*\*PostgREST API\*\*:  
\`\`\`

https://\<project\>.supabase.co/rest/v1/{schema}.{table}

\`\`\`\`

\#\#\# Example — Fetching Public Trends  
\`\`\`bash  
curl "https://\<project\>.supabase.co/rest/v1/intelligence.trends?limit=10" \\  
  \-H "apikey: \<SUPABASE\_ANON\_KEY\>" \\  
  \-H "Authorization: Bearer \<SUPABASE\_ANON\_KEY\>"  
\`\`\`\`

\#\#\# Example — Pushing Data (Content Autopilot)

\`\`\`bash  
curl \-X POST "https://\<project\>.supabase.co/rest/v1/intelligence.trends" \\  
  \-H "apikey: \<SUPABASE\_SERVICE\_ROLE\_KEY\>" \\  
  \-H "Authorization: Bearer \<SUPABASE\_SERVICE\_ROLE\_KEY\>" \\  
  \-H "Content-Type: application/json" \\  
  \-d '{  
    "cluster\_topic": "AI in Healthcare",  
    "internal\_trend\_score": 87.3,  
    "sentiment\_label": "Positive"  
  }'  
\`\`\`

\---

\#\# 🔄 Data Ingestion Pipeline

| Stage                   | Source                                           | Destination                                | Method                                    |  
| \----------------------- | \------------------------------------------------ | \------------------------------------------ | \----------------------------------------- |  
| 1️⃣ Raw Data Collection | Apify Actors (News, SAPS, Amazon, YouTube, etc.) | Preprocessors                              | HTTP/AIO ingestion                        |  
| 2️⃣ Data Normalization  | Preprocessor/Analyzer Actors                     | Topic Trend Aggregator / Sentiment Compass | Structured JSON output                    |  
| 3️⃣ Central Ingestion   | Content Autopilot                                | Supabase                                   | Direct REST API POST using \`service\_role\` |  
| 4️⃣ Data Consumption    | Dashboards, MyWard, Newsauce                     | Supabase REST / Realtime API               | Public read-only via \`anon\` key           |

\---

\#\# 🧮 Data Governance

\* \*\*Retention Policy:\*\* All data older than 6 months may be archived to cold storage.  
\* \*\*Audit Logs:\*\* Supabase stores function logs for all service-role writes.  
\* \*\*Backups:\*\* Daily automated backups via Supabase storage replication.  
\* \*\*Sensitive Data:\*\* No PII is stored outside of the \`crime\_intelligence\` schema.

\---

\#\# 🧰 Maintenance Procedures

1\. \*\*Schema Changes\*\*

   \* New schema → Add RLS  
   \* Update policies → Drop and reapply with \`DROP POLICY IF EXISTS\`  
   \* Migrations versioned in \`/database/migrations/\`

2\. \*\*API Testing\*\*

   \* Use \`rls\_sanity\_check.sql\` for periodic validation of RLS  
   \* Validate public endpoints respond with HTTP \`200\` and not \`403\`

3\. \*\*Supabase Keys\*\*

   \* \`SUPABASE\_URL\` → Base REST URL  
   \* \`SUPABASE\_ANON\_KEY\` → Public dashboards and site widgets  
   \* \`SUPABASE\_SERVICE\_ROLE\_KEY\` → Used by internal automation pipelines only (never client-side)

\---

\#\# 🧭 Future Additions

| Feature                  | Description                                                                       |  
| \------------------------ | \--------------------------------------------------------------------------------- |  
| 🛰️ Nuclear Intelligence | Specialized domain for energy sector data, integrated into \`intelligence.domains\` |  
| 🧬 Fighting Intelligence | Tracks global fight events, integrated with topic & sentiment engines             |  
| 🏙️ Civic Data Expansion | Integration with municipal feeds for safety and infrastructure data               |  
| 💼 Visita Business AI    | Personalized dashboards for businesses using aggregated insights                  |  
| 🌍 Global API Layer      | Unified Visita Intelligence API for partner integrations                          |

\---

\#\# 🏁 Conclusion

Visita’s Supabase is now \*\*production-grade\*\*, \*\*role-secured\*\*, and \*\*ready for integration\*\* across all Visita Intelligence and Business services.

This structure supports:

\* Centralized data ingestion  
\* Multi-sector intelligence (Civic, Business, Crime, AI)  
\* Secure access separation  
\* Long-term scalability for new domains

\---

\*\*Maintained by:\*\*  
Visita Systems — Intelligence, AI & Civic Data Division  
📧 \[support@visita.co.za\](mailto:support@visita.co.za) | 🌐 \[https://visita.co.za\](https://visita.co.za)

\`\`\`

\---

Would you like me to add an \*\*“API Catalog” appendix\*\* next — listing every REST endpoint, its supported query parameters (filtering, range, ordering), and whether it’s public or private? It would complete the API developer documentation for Visita Intelligence.  
\`\`\`

