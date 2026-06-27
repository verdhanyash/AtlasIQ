# Technical & Business Problem Compendium — 2nd Year Batch (B.Tech CSE-AIDE)

**Duration:** 22 June 2026 → 26 July 2026 (5 weeks)
**Companion to:** 01_Workflow_Guide.md
**Purpose:** For every problem statement, this document gives you the *business scenario*, the *problem to solve*, the *learning direction* (what to learn and at what depth), the *mini-extension* (what to add in week 3), the *3rd year extension path* (how to keep going), and the *deliverable shape*.

---

## How to Read This Document

Each problem statement follows this 7-section structure:

1. **Business Scenario** — the imagined company, its pain, and why this problem matters
2. **Problem Statement** — what you are specifically being asked to deliver
3. **Why This Matters for Placements (and Beyond)** — the long-term career signal
4. **Learning Direction** — what topics to cover, at what depth (the "map" — not tutorials)
5. **The Mini-Extension** — the small, scoped addition you build in Week 3 to go beyond the minimum
6. **3rd Year Extension Path** — how to keep building this project through 3rd year (and into the 3rd year internship)
7. **Final Deliverable Shape** — what the shipped product looks like

Pick ONE problem. Read its 7 sections fully. Then go back to Document 01 and follow the workflow.

---

# SEGMENT 1 — FOUNDATIONS OF ANALYTICS ENGINEERING

> Track you're on: Data Analyst · BI Analyst · Junior BA · Analytics Consultant
> By end of this internship you'll be able to: write SQL fluently, model data into a warehouse, build a stakeholder-facing dashboard, and tell a data story.

---

## G1. Student Performance Twin — Personal Academic Analytics

### 1. Business Scenario
You are a **Junior Data Analyst at a fictional edtech company, "ScoreLab"**, that wants to help college students understand their own academic trajectory. The product team has been given a research finding: students who see their own data visualised take 23% more corrective action than students who don't. They want a **personal analytics twin** — a dashboard that pulls together a student's own data (attendance, marks, assignment scores, LMS activity) and surfaces insights, predictions, and "what-if" scenarios.

You will use **your own academic data** (anonymised) as the test case. The output should be a tool your classmates would actually want to use.

### 2. Problem Statement
Build **MyTwin** — a personal academic analytics dashboard:
- **Data sources:** your own (synthesised if you don't want to share) — attendance, internal marks, assignment scores, LMS clicks, library checkouts if available
- **Warehouse:** 1 fact table (events) + 3-4 dimensions (course, assignment, time, location)
- **Core analyses:**
  - Cohort comparisons: where do you stand in your section, in your batch?
  - Trend analysis: marks trajectory, attendance trajectory
  - Correlation discovery: does attendance correlate with marks? (be careful — correlation ≠ causation; document this)
  - "What-if" simulator: "if I score X in the final, my overall is Y"
- **Dashboard:** 3 tabs — **My Snapshot · Trends · What-If**
- **Insights memo:** a 1-page written brief to "yourself" — what's working, what's not, what to change next semester

### 3. Why This Matters for Placements (and Beyond)
This is the cleanest possible analytics project you can build, and it teaches the most important skill: **turning raw data into a story someone acts on.** Every analyst role interviews on this exact pattern. Recruiters at **TCS, Accenture, Cognizant, Mphasis, Tiger Analytics, Latentview, Mu Sigma, JioMART, Razorpay BA, and every product company** will recognise the structure.

### 4. Learning Direction

**What to learn (at working depth, not mastery):**
- **SQL:** window functions, CTEs, aggregations, date functions. Aim for 30+ queries by end of internship.
- **Data modelling:** star schema, fact vs dimension, slowly changing dimensions (intro level).
- **dbt (intro):** staging → marts pattern, basic tests.
- **BI tool:** Streamlit, Plotly Dash, or Metabase. Pick one and learn it properly.
- **Statistics basics:** correlation, regression, confidence intervals (conceptual, not PhD-level).
- **Storytelling:** how to structure an insight memo (situation → complication → question → answer).

**What to skim (don't deep-dive):**
- Real-time analytics, ML-based predictions, governance.

### 5. The Mini-Extension
Add a **"Peer Benchmarking"** tab to the dashboard:
- Compare yourself against 3-4 anonymised peer profiles (you create these as "what-if I were like them")
- A "gap analysis" view: what would I need to do to match the top-performer profile?
- **Why this matters:** this is the simplest form of "prescriptive analytics" and it shows you can go beyond descriptive.

### 6. 3rd Year Extension Path
- **3rd year, month 1-2:** add a **dropout risk model** — predict, given current trajectory, your probability of dropping below a CGPA threshold
- **3rd year, month 3-4:** add a **study-recommendation engine** — "students with your profile who improved 1 CGPA point did X"
- **3rd year, month 5+:** turn it into a multi-tenant SaaS — your classmates can sign up, connect their LMS, get their own twin
- **3rd year internship fit:** this becomes your **Insights & Decision Intelligence** project (A1 Churn Radar is a natural extension — same data flow, different business)

### 7. Final Deliverable Shape
- GitHub repo with: dbt project (or SQL transforms), Streamlit/Dash app, README, requirements.txt, 3 ADRs (tech stack choice, dashboard tool choice, modelling choice)
- Hosted dashboard URL
- `insights_memo.md` — 1-page brief
- `sql_portfolio.sql` — 10+ queries you wrote, with comments
- 3-min Loom walkthrough
- 2-3 resume bullets (use this project as your first analytics project)

---

## G2. CampusOps 360 — Real Campus Operations Analytics

### 1. Business Scenario
You are a **Junior Business Analyst at LPU's Operations team**. The team manages mess food, hostel maintenance, transport, and library — and is drowning in complaints but starving for data. The Director of Operations wants a single dashboard that shows: **"Where is the operation failing, by when, by where, and by how much?"** — across all 4 functions. You will work with synthetic but realistic data modelled on the patterns LPU actually has.

### 2. Problem Statement
Build **CampusOps 360**:
- **4 data domains:** mess food, hostel, transport, library
- **For each domain, ingest + clean + model 3-6 months of synthetic data:**
  - Mess: daily menu, headcount per slot, wastage (kg), cost per plate, complaint count
  - Hostel: maintenance tickets (category, severity, resolution time), occupancy, complaints
  - Transport: route-wise ridership, on-time %, breakdowns, fuel use
  - Library: footfall, book issues, e-resource usage, late returns
- **Cross-domain analytics:**
  - "Is mess footfall down on exam days? Does that correlate with library footfall up?"
  - "Which hostels have the most unresolved maintenance tickets > 7 days?"
  - "Which transport routes have the worst on-time % at which time of day?"
- **Dashboard:** 4 tabs (one per domain) + 1 cross-domain "Operations Health" tab
- **Insights memo:** 2-page brief to the Director of Operations with 3 specific recommendations

### 3. Why This Matters for Placements
This is exactly the kind of work junior analysts do in their first 6 months at any large organisation — **multi-stakeholder data consolidation, cross-functional dashboards, business-facing memos.** Strong signal for **TCS BA, Accenture AA, Cognizant, Mphasis, Genpact, Latentview, and any in-house analyst role.**

### 4. Learning Direction

**What to learn:**
- Data modelling across heterogeneous sources
- Cleaning and standardising dirty data
- Cross-domain joins and aggregations
- Dashboard design for non-technical audiences
- Writing executive memos (1-page, structured)
- Time-series basics (trends, seasonality, anomalies)

**What to skim:**
- ML on time series, real-time pipelines

### 5. The Mini-Extension
Add a **"Complaint-to-Resolution" funnel** to the Hostel tab:
- Map maintenance ticket lifecycle: open → assigned → in-progress → resolved → verified
- Compute drop-off at each stage, average time per stage
- Identify the worst-performing stage
- **Why this matters:** process analytics is a step up from descriptive analytics; it shows you can think about operations, not just data.

### 6. 3rd Year Extension Path
- Add a **predictive maintenance model** for hostel tickets
- Add a **demand forecasting** module for mess food
- Add a **route optimisation** analysis for transport
- Add an **anomaly detection** layer that alerts the ops team
- **3rd year internship fit:** this becomes **A3 Funnel Autopsy** (just swap campus ops for fintech marketing) — same structure, much higher stakes

### 7. Final Deliverable Shape
Same shape as G1.

---

## G3. LocalBiz Insights — Partner with a Real Local Business

### 1. Business Scenario
You are a **freelance data analyst** taking on your first paying-ish client: a real local business near LPU — a kirana store, a salon, a gym, a tuition center, a café, a PG. They have data (POS, billing, UPI, attendance, etc.) but no idea what to do with it. You will meet them (or simulate the meeting), understand their pain, and build a dashboard + 1-page brief that genuinely helps them.

This is the **only project in this internship that involves real data and a real stakeholder.** It's the hardest, and the most rewarding.

### 2. Problem Statement
Build **BizLens** for one real local business:
- **Stakeholder interview:** understand what decisions they make daily/weekly and what data would help
- **Data acquisition:** get their data (with permission) — could be a CSV, a Google Sheet, photos of registers, anything
- **Clean + model:** handle real-world mess (missing entries, typos, inconsistent formats)
- **3-5 KPIs the stakeholder actually cares about:** e.g., for a salon — "average ticket size by stylist, no-show rate by day, repeat customer %, revenue per chair-hour"
- **Dashboard:** 2-3 tabs, mobile-friendly (they'll check on their phone)
- **Insights brief:** 1-2 pages, plain language, **"here's what to change on Monday"**

### 3. Why This Matters for Placements
This is the **unicorn project** for 2nd years. Most candidates have toy data. You will have a real stakeholder, real data, real recommendations. In interviews at **any company**, when you say "I built a dashboard for a salon and they changed their staffing based on my analysis," the room goes quiet. This is the project that gets you interviews, period.

### 4. Learning Direction

**What to learn:**
- Stakeholder communication: how to ask the right questions, how to scope a project
- Data cleaning: handling real-world mess
- Domain understanding: read about the business (a salon's KPIs are different from a kirana's)
- Visualisation for non-technical audiences: less is more
- Writing for a business audience, not a tech audience
- Delivery: how to present findings to a stakeholder who doesn't care about your tech stack

**What to skim:**
- Advanced ML, complex data modelling

### 5. The Mini-Extension
Add a **"What changed?" tracker** to the dashboard:
- A weekly snapshot of the top 3 KPIs
- A simple trend line: are they going up or down?
- An auto-generated "this week vs last week" summary
- **Why this matters:** it shows the stakeholder the dashboard is a living tool, not a one-time report. This is what analytics actually looks like in the real world.

### 6. 3rd Year Extension Path
- If the business is interested, **keep working with them** through 3rd year — that's a side hustle and a portfolio piece
- Generalise the solution for 2-3 more businesses — you now have a "productised analytics service"
- **3rd year internship fit:** the "stakeholder interview + insights brief" pattern is exactly what **A1-A4** in the 3rd year internship expects. You will be way ahead.

### 7. Final Deliverable Shape
- GitHub repo with: data (anonymised if needed), cleaning scripts, dashboard, README
- Hosted dashboard URL
- `stakeholder_brief.pdf` — the 1-2 page brief you gave the business owner
- `sql_portfolio.sql`
- 3-min Loom walking through the dashboard AND the brief
- 2-3 resume bullets framed as "freelance / consulting" work (this is a *signal*, use it)

---

# SEGMENT 2 — FOUNDATIONS OF DATA ENGINEERING

> Track you're on: Data Engineer · Analytics Engineer · Junior DE
> By end of this internship you'll be able to: build a pipeline from source to warehouse, containerise it, deploy it, test it, and document it.

---

## H1. APIs to Warehouse — The Classic DE Starter

### 1. Business Scenario
You are a **Junior Data Engineer at "PulseMetrics"**, a startup that aggregates public data and sells insights. Your first task: pick a public API (GitHub, weather, crypto, sports, traffic, public health), ingest it on a schedule into a warehouse, transform it with dbt, and expose it to a BI tool. The CTO says: "If you can do this end-to-end, you can do 70% of the work I hire for."

### 2. Problem Statement
Build **PipeOne**:
- **Pick a public API** (recommend: GitHub Events for high volume, or OpenWeather for geography). Document why in an ADR.
- **Ingestion:** scheduled (cron / Airflow / Dagster — local is fine), with proper error handling, retries, and idempotency
- **Warehouse:** Postgres (local Docker) OR BigQuery/Snowflake free tier OR DuckDB
- **Transformations:** dbt project with staging → intermediate → marts, with at least 5 models
- **Tests:** dbt tests + at least 2 custom data quality tests
- **BI:** Metabase (Docker) OR Streamlit OR Preset
- **Documentation:** dbt docs auto-generated, plus a top-level README
- **Containerise the whole thing:** Docker Compose that brings up the warehouse, the orchestrator, dbt, and the BI tool

### 3. Why This Matters for Placements
This is the **literal entry-level DE interview loop**. Walk into **Amazon, Flipkart, Razorpay, PhonePe, Paytm, NPCI, Mphasis, Cognizant DataPractice, Tiger Analytics, and ask "what's your first project?"** — you'll hear some version of this. Master this, and you have 70% of the answer to "do you have production DE experience?".

### 4. Learning Direction

**What to learn:**
- **SQL:** deeply. Window functions, CTEs, joins, aggregations. This is your primary tool.
- **dbt:** the de-facto analytics engineering framework. Models, tests, sources, docs.
- **Python:** data structures, requests, pandas, error handling, logging.
- **Orchestration:** one of Airflow / Dagster / Prefect / cron. Just learn one properly.
- **Docker:** basics. Compose, networks, volumes.
- **APIs:** REST, pagination, rate limits, auth (API keys, OAuth basics).
- **Data modelling:** star schema, slowly changing dimensions intro.

**What to skim:**
- Kafka, Spark, Flink, Kubernetes (these come in 3rd year)

### 5. The Mini-Extension
Add a **second source** to the pipeline:
- Same destination, same dbt project, just one more connector
- e.g., GitHub Events + Hacker News top stories, both landing in the same warehouse, both feeding the same BI tool
- **Why this matters:** shows you can generalise, not just follow a tutorial. This is the difference between "I did a project" and "I can build pipelines."

### 6. 3rd Year Extension Path
- Add a **streaming source** → Kafka → Spark Streaming (H2 has the streaming part; H1 has the batch part)
- Add **data contracts** and a **catalog**
- Add a **data quality framework** (Great Expectations)
- Add **CI/CD** with GitHub Actions
- **3rd year internship fit:** this becomes **B1 Unified Commerce Lakehouse** with the multi-source complexity

### 7. Final Deliverable Shape
- GitHub repo with: ingestion code, dbt project, Docker Compose, README, 3 ADRs
- Live demo URL (host the BI tool somewhere free)
- 3-min Loom
- 2-3 resume bullets

---

## H2. CSV Hell Pipeline — Handling the Messy Reality

### 1. Business Scenario
You are a **Junior Data Engineer at "SupplierSync Co."**, a B2B startup that ingests supplier data from 50+ SMB suppliers. The reality: every supplier sends a daily CSV, and **no two CSVs are the same**. Different column names for the same field (`product_id` / `sku` / `item_code`). Different date formats. Different encodings. Some arrive late, some have duplicate rows, some have rows that fail to parse. The current "pipeline" is 5 manual hours/day of cleanup in Excel. You will automate it.

### 2. Problem Statement
Build **CleanSweep**:
- **5 simulated supplier CSVs** — different shapes, different quirks (one has a header row in Spanish, one has a footer summary row, one is in Excel xlsx with merged cells, one has inconsistent date formats, one has duplicate rows)
- **Ingestion layer:** detects file type, encoding, schema; standardises column names; reports per-file diagnostics
- **Validation layer:** schema enforcement, value range checks, business rules (e.g., price > 0)
- **Storage:** raw (preserved) → staging (cleaned) → conformed (canonical schema)
- **Quarantine:** bad rows don't fail the pipeline; they go to a `quarantine` table with a reason, for human review
- **dbt project:** at least 6 models, with tests on the canonical layer
- **Observability:** a simple dashboard showing: files processed today, rows accepted, rows quarantined, top 3 quarantine reasons
- **Replay:** the ability to re-process yesterday's file (idempotency check)

### 3. Why This Matters for Placements
**The real world of data engineering is messy file ingestion.** This is what DEs do 50% of the time. Recruiters at **any B2B SaaS, any supply chain co, any fintech with KYC docs, any healthcare co with provider data** will recognise this. It's the most "honest" DE project you can do.

### 4. Learning Direction

**What to learn:**
- File format handling: CSV, TSV, xlsx, JSON, fixed-width
- Encoding detection: chardet, ftfy
- Schema evolution: handling new columns gracefully
- Data validation: Great Expectations OR Pandera OR hand-rolled
- dbt: same as H1
- Idempotency: what it means, how to design for it
- Error handling philosophy: fail-fast vs fail-soft (quarantine is fail-soft)
- Logging and observability basics

**What to skim:**
- Streaming, ML, governance

### 5. The Mini-Extension
Add a **schema-drift detector**:
- The pipeline detects when a new CSV has a column that wasn't in the previous file
- It does NOT fail — it logs a `schema_change` event, adds the column to a `schema_history` table, and continues
- A small UI/email alert when schema changes
- **Why this matters:** schema drift is a top-3 production data problem. Showing you can handle it is a big win.

### 6. 3rd Year Extension Path
- Move from local file drops to **S3 / SFTP / email-attachment** ingestion
- Add a **streaming source** alongside the batch
- Add **data contracts** (one per supplier)
- Add a **catalog** (DataHub, OpenMetadata)
- **3rd year internship fit:** this becomes **B4 CDC Replicator** when you replace CSVs with CDC from OLTP — same patterns, real-time.

### 7. Final Deliverable Shape
Same shape as H1, plus a `quarantine_dashboard.png` showing the failure modes caught.

---

## H3. Real-time Hashtag Pulse — Streaming Starter

### 1. Business Scenario
You are a **Junior Streaming Engineer at "TrendWatch", a social listening startup** that gives brands real-time visibility into what people are saying about them. Your first project: build a pipeline that streams public social data (Twitter/X API or Reddit), processes it in real time, and surfaces a live dashboard of sentiment, top entities, and topic drift.

This is the **only project in the 2nd year DE track that introduces streaming.** It's a foundation for the 3rd year B2 Clickstream project.

### 2. Problem Statement
Build **PulseLite**:
- **Source:** Reddit public API (e.g., r/india, r/cricket) OR simulated Twitter data — document the choice
- **Ingest:** Kafka topic, with a simple producer that polls the API and emits events
- **Process:** Kafka Streams OR a simple PySpark Structured Streaming job — compute:
  - Sentiment per post (a small model OR VADER)
  - Top entities (regex + frequency)
  - Volume per minute
  - Topic drift (rolling window of top words)
- **Sink:** a small datastore (ClickHouse local / DuckDB / Postgres) for the live dashboard
- **Dashboard:** live-updating view (Streamlit with auto-refresh, or a simple real-time chart) showing the 4 metrics above
- **Docker Compose** for the whole stack

### 3. Why This Matters for Placements
Streaming is the most under-taught and most-hired DE skill in 2026. Even a basic "Kafka + dashboard" project is a differentiator. **Razorpay, PhonePe, CRED, Swiggy, Zomato, Dream11, MPL, ShareChat, and all ad-tech** hire on this.

### 4. Learning Direction

**What to learn:**
- Kafka fundamentals: topics, partitions, producers, consumers, consumer groups
- Streaming concepts: event time vs processing time, windowing, out-of-order events
- Python OR Scala: pick one
- Basic NLP: VADER for sentiment, regex for entity extraction
- Docker Compose for multi-service stacks
- Real-time visualisation: auto-refreshing dashboards

**What to skim:**
- Exactly-once semantics, watermarks, Flink internals (3rd year)

### 5. The Mini-Extension
Add a **simple anomaly detector**:
- Compute the rolling 5-minute average volume per topic
- Alert (log + dashboard marker) when current volume > 3x rolling average
- **Why this matters:** anomaly detection on streams is the gateway to real-time monitoring. It's a 20-line addition that shows real thinking.

### 6. 3rd Year Extension Path
- Add **exactly-once** end-to-end
- Add **late-arrival handling** with watermarks
- Add a **second stream** with stream-stream joins
- Move to **Flink** from Kafka Streams / PySpark Streaming
- **3rd year internship fit:** this becomes **B2 Clickstream Telemetry Pipeline** — the only difference is scale and sophistication.

### 7. Final Deliverable Shape
Same shape as H1, plus a recorded demo of the live dashboard updating.

---

# SEGMENT 3 — FOUNDATIONS OF APPLIED MACHINE LEARNING

> Track you're on: ML Engineer · AI Engineer · Junior Data Scientist
> By end of this internship you'll be able to: train a model, evaluate it properly, deploy it behind a simple UI, and explain it to a non-technical stakeholder.

---

## I1. Tabular ML Zoo — The Classic ML Lifecycle

### 1. Business Scenario
You are a **Junior ML Engineer at "LoanEasy", a fintech** that offers personal loans. The Head of Risk wants to know: "Can a model predict which loan applicants will default in the first 90 days, using only data we have at application time?" This is the most common real-world ML problem in BFSI — and a perfect lifecycle project for you.

### 2. Problem Statement
Build **RiskRadar**:
- **Dataset:** public — Lending Club, Home Credit Default Risk, or a synthetic one you generate (the Kaggle "Home Credit" dataset is recommended)
- **Full lifecycle:**
  1. **EDA:** understand the data, missingness, distributions
  2. **Feature engineering:** aggregations, ratios, date features, target encoding
  3. **Models:** baseline (logistic regression) + at least 3 more (LightGBM, XGBoost, CatBoost) — compare
  4. **Validation:** proper time-based split (NO random shuffle for time-sensitive data)
  5. **Metrics:** AUC, recall@K, calibration plot, business cost (cost of false negative vs false positive)
  6. **Explainability:** SHAP global + local for a few examples
  7. **Deployment:** a Streamlit app where you input applicant data and get a risk score + SHAP explanation
- **Model card:** following the Mitchell et al. format, 1-2 pages
- **README:** explains the full lifecycle in a way a 2nd year reading your repo in 6 months could follow

### 3. Why This Matters for Placements
**Every ML / DS / AI role interviews on tabular ML.** Lending risk, churn, fraud, retention, demand forecasting — they all use this exact pipeline. Master this and you can walk into **any** ML interview at a fintech, retail-tech, healthtech, edtech, or service company.

### 4. Learning Direction

**What to learn:**
- **Pandas + NumPy:** the bread and butter. Aim for fluency.
- **Scikit-learn:** pipelines, ColumnTransformer, cross-validation, GridSearchCV
- **Gradient boosting:** LightGBM (recommended), XGBoost, CatBoost — at least one to working depth
- **Feature engineering:** the most important skill. Time, target encoding, aggregations, ratios.
- **Validation:** time-based split, group-based split, leakage detection
- **Metrics:** AUC, precision, recall, F1, calibration, business cost-weighted metrics
- **Explainability:** SHAP (tree explainer), basic interpretation
- **Deployment:** Streamlit / Gradio for the demo
- **Model card:** standard format

**What to skim:**
- Deep learning (not needed for tabular), transformers, MLOps tooling (3rd year)

### 5. The Mini-Extension
Add a **"Fairness Audit"** section to your model card:
- Pick 2-3 protected attributes (gender, age, location, etc.)
- Compute disparate impact ratio and equal opportunity difference
- Document findings and discuss trade-offs
- **Why this matters:** fairness is now table-stakes for any production ML. Mentioning it puts you ahead of 90% of candidates.

### 6. 3rd Year Extension Path
- Wrap it in a **proper MLOps loop** (D2 Continuous Training Platform) — drift detection, retraining, canary deploy
- Add a **feature store** (D1) so features can be reused by other models
- Add **monitoring + governance** (D4)
- **3rd year internship fit:** this becomes the productionised version of itself — same model, real engineering around it.

### 7. Final Deliverable Shape
- GitHub repo: data (or link), notebooks + scripts, model artefacts, Streamlit app, model card, README, 3 ADRs
- Live demo URL
- 3-min Loom
- 2-3 resume bullets

---

## I2. Document Q&A — RAG over a Focused Corpus

### 1. Business Scenario
You are a **Junior AI Engineer at "StudyBuddy EdTech"**. The product team wants a "talk to your textbook" feature: a student uploads a PDF of their course textbook (or a set of research papers, or their college handbook), and can ask questions, get answers with citations. This is the cleanest possible "applied LLM" starter project.

### 2. Problem Statement
Build **AskMyBook**:
- **Corpus:** your own choice — a course textbook (PDF), a set of research papers, your college handbook, a domain-specific docs site
- **Ingestion:** PDF parsing (PyMuPDF or Unstructured.io), chunking (semantic + structural)
- **Embeddings:** OpenAI OR Voyage OR open-source (BGE, E5, Nomic)
- **Vector DB:** Qdrant OR Weaviate OR pgvector OR ChromaDB
- **Retrieval:** hybrid (BM25 + dense), top-k
- **Generation:** GPT-4o-mini OR Claude Haiku OR open-source (Qwen, Llama) — your choice, justify
- **UI:** Streamlit or Gradio, with **inline citations** (page number + quoted text)
- **Eval:** 20+ test questions, with human-rated answers on 3 axes (correctness, citation precision, completeness)
- **Guardrails:** "I don't know" when evidence is weak; refusal on out-of-corpus questions

### 3. Why This Matters for Placements
RAG is **the most common GenAI project** in 2026 placements. Every GenAI job description asks for it. Demonstrating RAG done well — with proper eval, citations, and guardrails — is the difference between "I built a chatbot" and "I can build production GenAI."

### 4. Learning Direction

**What to learn:**
- **Document parsing:** PDFs (text + tables + images), chunking strategies
- **Embeddings:** what they are, what makes a good one, when to use which
- **Vector DBs:** how they index, how ANN works (conceptual), metadata filtering
- **Retrieval:** BM25 (the old way that still works), dense retrieval, hybrid
- **Prompting:** basic prompting, structured outputs, citation enforcement
- **Eval:** Ragas OR DeepEval OR hand-rolled; LLM-as-judge
- **Basics of guardrails:** input sanitisation, output validation
- **Cost & latency:** token counting, model selection tradeoffs

**What to skim:**
- Fine-tuning, multi-modal, agentic patterns (3rd year)

### 5. The Mini-Extension
Add a **"Compare Two Documents"** feature:
- Upload 2 PDFs (e.g., two versions of a syllabus, or two research papers)
- Ask: "what's different between these on topic X?"
- The system retrieves from both, compares, and answers
- **Why this matters:** multi-document reasoning is a step up from single-doc RAG. Recruiters will notice.

### 6. 3rd Year Extension Path
- Move from 1 corpus to **enterprise mess** (4+ source types, dirty data) → E3 in 3rd year
- Add **fine-tuning** of a small model on your domain → E4
- Add **agentic patterns** for complex queries → E1, E2
- **3rd year internship fit:** this is a direct subset of E3. The 3rd year version is just bigger, messier, and more rigorously evaluated.

### 7. Final Deliverable Shape
- GitHub repo: ingest, chunk, embed, retrieve, generate, eval, app
- Live demo URL
- Eval report (20+ Q&A pairs with scores)
- 3 ADRs
- 3-min Loom
- 2-3 resume bullets

---

## I3. Vision Starter — Image Classification / Detection

### 1. Business Scenario
You are a **Junior CV Engineer at "AgriScan", an agritech startup**. Farmers send photos of their crops, the app returns "this leaf has early blight" or "this fruit is ready to harvest." You'll build the model and a small web app that demonstrates it.

### 2. Problem Statement
Build **SeeIt**:
- **Dataset:** pick one — PlantVillage (leaf disease, recommended), TrashNet (waste sorting), or a Kaggle traffic-sign / pothole dataset
- **Task:** classification (image → class) OR detection (image → bounding boxes + classes)
- **Model:** transfer learning from a pretrained ResNet / EfficientNet / YOLO (your choice, justify)
- **Training pipeline:** proper train/val/test split, augmentation (basic: rotation, flip, colour jitter), early stopping, learning rate scheduling
- **Evaluation:** per-class precision/recall/F1, confusion matrix, top-5 misclassifications visualised
- **Deployment:** a Streamlit / Gradio app where you can upload an image and get a prediction + confidence
- **Export:** ONNX export, with a note on edge deployment feasibility

### 3. Why This Matters for Placements
**CV is the most-hired niche in India's manufacturing/agritech/healthtech.** Companies like **Tata Steel, Mahindra, Samsung, Flex, Wistron, Bharat Electronics, CropIn, Intello Labs, Fasal, Plantix** hire CV engineers. A working CV project with deployment is interview gold.

### 4. Learning Direction

**What to learn:**
- **PyTorch basics:** tensors, datasets, dataloaders, training loop
- **Transfer learning:** using pretrained models, fine-tuning strategies (freeze/unfreeze, discriminative LRs)
- **Augmentation:** torchvision OR albumentations
- **Classification metrics:** per-class metrics, confusion matrix, calibration
- **Detection basics (if doing detection):** YOLO, mAP, IoU, NMS
- **Deployment:** Streamlit/Gradio for demo
- **Export:** ONNX, basic understanding of edge deployment

**What to skim:**
- Video, 3D, multi-modal (3rd year and beyond)

### 5. The Mini-Extension
Add a **"Show me why"** explanation:
- Use Grad-CAM (or similar) to highlight which part of the image led to the prediction
- Overlay on the uploaded image
- **Why this matters:** explainability is the difference between "the model is right" and "the model is right AND I can show you why." Recruiters love this.

### 6. 3rd Year Extension Path
- Move from classification to **detection** (if you started with classification)
- Add **active learning loop** (C2)
- Add **drift monitoring** (D2)
- Move to **edge deployment** with TensorRT / OpenVINO
- **3rd year internship fit:** this becomes **C2 Visual Quality Inspection** — same ML, much more engineering around it.

### 7. Final Deliverable Shape
Same shape as I1, I2.

---

# SEGMENT 4 — FOUNDATIONS OF CLOUD & DEVOPS

> Track you're on: Cloud Engineer · DevOps Engineer · SRE · Platform Engineer
> By end of this internship you'll be able to: deploy an app, set up CI/CD, containerise it, monitor it, and explain your infrastructure.

---

## J1. Portfolio-as-a-Service — Deploy Your Own Site Properly

### 1. Business Scenario
You are a **Junior DevOps Engineer at "Personal Brand Co."**, which is just you. The mission: deploy your **own developer portfolio site** with the kind of infrastructure rigor a real startup would use. CI/CD, custom domain, monitoring, backups. By the time you're done, you'll have a site that impresses recruiters **and** the infrastructure chops to back it up.

### 2. Problem Statement
Build **MyDeploy**:
- **The site:** a static OR simple dynamic site (Next.js / Hugo / Jekyll / plain HTML — your choice)
- **Containerised:** Dockerfile, multi-stage build, small image size (<200MB)
- **CI/CD:** GitHub Actions — on every push to main → run tests → build image → push to registry → deploy
- **Hosting:** free-tier cloud (Vercel, Netlify, Render, Fly.io, Railway) OR a free-tier VM (Oracle Cloud free tier, GCP free tier)
- **Custom domain:** free domain (e.g., freenom, .tk, or buy a cheap one)
- **HTTPS:** Let's Encrypt via cert-manager or auto-handled by the platform
- **Monitoring:** Uptime Kuma (self-hosted) or BetterStack free tier
- **Backups:** automated weekly backup of any stateful data (DB, files) to S3-compatible storage
- **Documentation:** a top-level README that explains the entire infrastructure

### 3. Why This Matters for Placements
Recruiters will literally visit your portfolio site. **A site that loads fast, has HTTPS, and shows a green uptime badge screams "I know what I'm doing."** This project is also the cleanest possible introduction to **Docker + CI/CD + cloud + monitoring** — the exact stack every DevOps interview asks about. Companies hiring for this: **Freshworks, Razorpay, Chargebee, NPCI, JP Morgan, Wells Fargo, all DevOps-first startups, every service-company DevOps track.**

### 4. Learning Direction

**What to learn:**
- **Git:** branching, PRs, rebasing, conflict resolution
- **Docker:** Dockerfile, multi-stage, image layers, .dockerignore
- **GitHub Actions:** workflows, secrets, caching, matrix builds
- **Cloud basics:** 1 of AWS / GCP / Azure free tier, or a PaaS like Vercel/Render
- **DNS:** A records, CNAME, TTL
- **HTTPS:** Let's Encrypt, cert renewal
- **Monitoring:** uptime, response time, alerting
- **IaC intro:** even a simple shell script that sets up your VM counts

**What to skim:**
- Kubernetes, Terraform, advanced networking (3rd year)

### 5. The Mini-Extension
Add a **"Chaos Test"** to your deployment:
- A GitHub Action that, once a week, kills the running container and verifies the monitoring alerts fire and the site recovers
- **Why this matters:** chaos testing is the difference between "I deployed it" and "I trust my deployment." Even a toy version of this is impressive.

### 6. 3rd Year Extension Path
- Move from PaaS to **Kubernetes** (EKS / GKE / kind locally) → F4
- Add a **multi-service architecture** (frontend + backend + DB) with proper CI/CD
- Add **Terraform** for full IaC
- Add a **service mesh** or at least proper observability (Prometheus + Grafana)
- **3rd year internship fit:** this becomes **F1 Multi-Tenant SaaS Backbone** or **F4 GitOps Reference Platform**.

### 7. Final Deliverable Shape
- GitHub repo: site code, Dockerfile, GitHub Actions workflows, infra setup scripts, README, 3 ADRs
- Live site URL
- 3-min Loom walking through the site AND the CI/CD pipeline
- 2-3 resume bullets

---

## J2. Internal Tool Backbone — Build a Small But Real Tool

### 1. Business Scenario
You are a **Junior Backend/DevOps Engineer at "ClubHub"** — the platform that runs LPU's 200+ student clubs. Currently clubs manage events with Google Forms + WhatsApp groups, which is chaos. The Student Affairs office wants a **simple internal tool**: a club-event manager where clubs can create events, students can RSVP, attendance is tracked, and reports are auto-generated. You will build the MVP.

### 2. Problem Statement
Build **EventHub**:
- **Stack:** any — FastAPI + Postgres + simple frontend (Streamlit / React / Next.js)
- **Auth:** simple email/password (or magic link)
- **Entities:** Club, Event, RSVP, Attendance, User
- **Features:**
  - Club admin: create event, see RSVPs, mark attendance
  - Student: browse events, RSVP, see "my events"
  - Coordinator: see reports (events per club, attendance rate, top events)
- **API:** REST, with at least 10 endpoints, documented (OpenAPI auto-docs)
- **Tests:** at least 5 unit tests + 1 end-to-end test
- **Containerised:** Docker Compose for the whole stack
- **CI/CD:** GitHub Actions → test → build → deploy to free tier
- **Live deployment:** a real URL

### 3. Why This Matters for Placements
This is the **classic "I built a full-stack app"** project. Backend + frontend + DB + auth + tests + deploy. **Every** full-stack, backend, and DevOps interview has a version of this. Recruiters at **Razorpay, Cred, Groww, Meesho, Urban Company, Myntra, Flipkart, all service companies, and every product startup** hire on this.

### 4. Learning Direction

**What to learn:**
- **One backend framework:** FastAPI (Python) or Express (Node) or Spring Boot (Java) — your choice
- **One frontend framework:** Streamlit (Python) or React (heavy) or just server-rendered HTML
- **SQL:** schema design, joins, migrations
- **Auth basics:** password hashing (bcrypt), sessions vs JWT
- **Testing:** pytest (or equivalent), unit + integration
- **Containerisation:** Docker, Docker Compose
- **CI/CD:** GitHub Actions
- **API design:** REST conventions, status codes, error handling

**What to skim:**
- Microservices, Kubernetes, advanced auth (3rd year)

### 5. The Mini-Extension
Add a **"Notification System"** to the tool:
- When a user RSVPs, they get an email (use SendGrid free tier or a stub)
- 24h before the event, a reminder email
- When attendance is marked, a confirmation email
- **Why this matters:** async workflows + external integrations are a step up from "just a CRUD app." Recruiters notice.

### 6. 3rd Year Extension Path
- Add **multi-tenancy** (one ClubHub instance, many clubs with isolation) → F1
- Add **observability** (Prometheus + Grafana + OpenTelemetry)
- Move to **Kubernetes**
- Add **chaos testing**
- **3rd year internship fit:** this is the seed of F1, F2, or any backend-heavy 3rd year project.

### 7. Final Deliverable Shape
- GitHub repo: backend, frontend, DB migrations, tests, Docker Compose, GitHub Actions, README, 3 ADRs
- Live deployment URL
- 3-min Loom
- 2-3 resume bullets

---

## J3. API Gateway & Rate Limiter — The Platform Engineer Starter

### 1. Business Scenario
You are a **Junior Platform Engineer at "GateKeeper Inc."**, which builds API infrastructure for SMBs. Your first project: stand up an **API gateway** in front of 2-3 public APIs (e.g., GitHub, OpenWeather, a public crypto API), add rate limiting, auth, request logging, and a Grafana dashboard showing traffic.

This is the cleanest possible "infrastructure-as-a-product" starter. The output is a working gateway you could put in front of a real company's APIs.

### 2. Problem Statement
Build **GateLite**:
- **Gateway:** Kong (in Docker) OR Traefik OR Tyk — pick one, justify
- **3 upstream APIs** to proxy: pick from public APIs (GitHub, OpenWeather, CoinGecko, etc.)
- **Rate limiting:** per-IP and per-API-key, with different limits per route
- **Auth:** simple API key auth at the gateway level
- **Request logging:** structured JSON logs, persisted
- **Metrics:** Prometheus exporter from the gateway, scraped by Prometheus
- **Dashboard:** Grafana with 3 panels — request rate, error rate, p95 latency
- **Documentation:** OpenAPI spec for the gateway routes
- **Containerised:** Docker Compose for everything

### 3. Why This Matters for Placements
**API gateways are the entry drug to platform engineering.** Every company that has APIs has a gateway story. This project teaches Docker, networking, observability, and infrastructure-as-code. Recruiters at **every DevOps / SRE / Platform role** interview on this. **Freshworks, Razorpay, Chargebee, Cred, all fintechs, all telcos, all banks' platform teams** — gateway experience is gold.

### 4. Learning Direction

**What to learn:**
- **Docker networking:** bridge networks, port mapping, service discovery
- **Reverse proxies / gateways:** what they do, how they work
- **Rate limiting algorithms:** token bucket, leaky bucket, fixed window — conceptual
- **Auth patterns:** API keys, basic auth, JWT intro
- **Observability:** Prometheus metrics, Grafana dashboards, structured logging
- **API specs:** OpenAPI / Swagger
- **Security basics:** TLS termination, secret management

**What to skim:**
- Service mesh (Istio, Linkerd), Kubernetes ingress, advanced auth (3rd year)

### 5. The Mini-Extension
Add a **"Quota Dashboard"** to Grafana:
- Per-API-key usage over time
- A "top consumers" panel
- An alert when any key hits 80% of its quota
- **Why this matters:** quota management is a real product concern. Showing you can build the dashboard that ops teams use is a step up from "I stood up a gateway."

### 6. 3rd Year Extension Path
- Move from Docker Compose to **Kubernetes** (EKS / GKE / kind) → F4
- Add **mTLS** between services
- Add a **service mesh**
- Add **chaos testing**
- **3rd year internship fit:** this is the seed of F1 (multi-tenant gateway), F2 (event-driven), or F4 (GitOps platform).

### 7. Final Deliverable Shape
Same shape as J1, J2.

---

# A Final Note for 2nd Years

You have **1 year + 1 summer** before placements. Here's the math:
- **This internship (now):** foundation, working software, basic confidence
- **3rd year semester:** extend the project you started here, add 1-2 more
- **3rd year internship (next summer):** production-grade, interview-defensible
- **Placements:** portfolio of 3-4 projects, with this one as the foundation

The companies you'll interview at in 12 months will look at your GitHub and ask: "what's the progression?" A clean, working 2nd year project that's clearly the seed of a 3rd year production project is **the** story you want to tell.

Pick. Read. Build. Extend. Ship.

See you on 22 June.
