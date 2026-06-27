# Internship Workflow Guide — 2nd Year Batch (B.Tech CSE-AIDE)

**Duration:** 22 June 2026 → 26 July 2026 (5 weeks, ~25 working days)
**Mode:** Individual work. No teams. No group projects.
**Outcome:** 1 shippable project + 1 mini-extension + 1 written reflection, all building a foundation for 3rd year placements.

---

## 1. The Big Picture

You are NOT here to do a placement-ready, interview-defensible, production-grade system. Not yet. You have one more year before placements — that year is where the production-grade work happens.

You ARE here to do three things:

| What | Why |
|------|-----|
| **Build a real, working, deployed thing** end-to-end | Prove to yourself you can. This is the foundation of 3rd year. |
| **Get a working command of the core tools** in your chosen track | The 3rd year internship will assume you know these. If you don't know them now, you'll drown later. |
| **Walk away with a project you can keep building** | Your 3rd year portfolio starts here. You will extend this project — not start a new one. |

The 3rd year internship is for "depth and polish." This one is for "I have the basics down and a real thing to show for it." Different game. Different output.

---

## 2. The 4 Segments (Pick ONE)

The 4 segments are deliberately broader than the 3rd year ones. We're not yet asking you to pick a niche like "MLOps" or "LLMOps" — you're picking a **track** you'll be in for the next 18 months.

| # | Segment Name | What you'll be ready to do in 3rd year | Target roles (after 3rd year) |
|---|--------------|----------------------------------------|-------------------------------|
| 1 | **Foundations of Analytics Engineering** | SQL fluently, dashboard built, warehouse modelled, data story told | Data Analyst · BI Analyst · Junior BA · Analytics Consultant |
| 2 | **Foundations of Data Engineering** | Pipeline built, containerised, deployed, with tests and a README | Data Engineer · Analytics Engineer · Junior DE |
| 3 | **Foundations of Applied Machine Learning** | Model trained, evaluated, deployed, with a frontend the user can poke | ML Engineer · AI Engineer · Junior Data Scientist |
| 4 | **Foundations of Cloud & DevOps** | App deployed, CI/CD set up, infrastructure-as-code, monitored | Cloud Engineer · DevOps Engineer · SRE · Platform Engineer |

**Rule:** Pick the segment that matches what you want to be doing daily in 3rd year and beyond. If you're torn between two, pick the one with **steeper industry demand** for your target city, not the one your friend picked.

---

## 3. The Problem Statements (Pick ONE within your segment)

You will find the full catalogue in **Document 02: Technical & Business Problem Compendium**.

Quick map:

**Segment 1 — Foundations of Analytics Engineering**
- G1. **Student Performance Twin** — Build a personal analytics dashboard from your own academic data
- G2. **CampusOps 360** — Analytics for a real campus operation (mess, hostel, transport, library)
- G3. **LocalBiz Insights** — Partner with a real local business, build KPIs from their data

**Segment 2 — Foundations of Data Engineering**
- H1. **APIs to Warehouse** — Ingest a public API → warehouse → BI tool, end-to-end
- H2. **CSV Hell Pipeline** — Handle 5 dirty, differently-shaped daily CSV drops into a clean warehouse
- H3. **Real-time Hashtag Pulse** — Stream public data → Kafka → Spark → live dashboard

**Segment 3 — Foundations of Applied ML**
- I1. **Tabular ML Zoo** — Kaggle-style problem, full lifecycle, end-to-end app
- I2. **Document Q&A** — RAG over a focused corpus (your textbook, a research area, college docs)
- I3. **Vision Starter** — Image classification / detection on a focused dataset, deployed

**Segment 4 — Foundations of Cloud & DevOps**
- J1. **Portfolio-as-a-Service** — Your own site, deployed, CI/CD, monitored
- J2. **Internal Tool Backbone** — A small but real internal tool (issue tracker, leave manager, club signup)
- J3. **API Gateway & Rate Limiter** — Kong/Traefik in front of public APIs with rate limiting and dashboards

---

## 4. The 5-Week Workflow

This is intentionally **slower-paced** than the 3rd year internship. You have more learning time, more mentor touchpoints, and more forgiving deadlines. Use the time to actually understand what you're doing — don't rush to ship.

### Pre-Internship (Before 22 June)
- Read this workflow guide fully.
- Skim the Technical & Business Problem Compendium.
- Identify your **top 2 segments** and **top 3 problem statements**.
- Set up: GitHub account (clean profile), Python 3.11+, Git, a code editor.
- Optional but recommended: Docker, a free-tier cloud account.
- Join the cohort Slack/Discord.
- **Pre-work assignment** (released 18 June, due 21 June): complete a 2-hour Python + Git refresher exercise. Not graded, but missing it sets you back.

### Day 1 (22 June, Mon) — Segment Orientation
- Morning: Welcome + segment overviews by mentors.
- Afternoon: Self-assessment + **Segment Ranker form** (skills, interests, target city, target role).
- Evening: Problem-statement teasers released. Mentors host 30-min open Q&A in their segment.

### Day 2 (23 June, Tue) — Problem Deep-Dive
- Per-segment deep-dives (scenario, scope, what you'll learn, what you'll ship).
- 1:1 with your segment mentor (15 min, sign up via form).

### Day 3 (24 June, Wed) — Lock Your Choice
- Submit your final segment + problem statement.
- Submit your **1-page Design Doc** by 11:59 PM (template provided). Don't worry about getting it perfect — mentor will iterate with you.

### Day 4-5 (25-26 June, Thu-Fri) — Setup + Architecture Review
- Day 4: 1:1 with mentor to walk through the design doc. Get sign-off on tech stack.
- Day 5: Repo created, environment set up, data exploration started. First commit pushed.
- **Friday EOD:** Architecture + tech stack signed off by mentor.

### Week 1 (29 Jun – 3 Jul) — Learn + Build Foundation
**Theme:** Set up the bones. Get the data layer working. **Spend at least 30% of the week learning the tools**, not just using them.
- Set up: repo, virtual env / Docker, data sources, basic tooling.
- Build: the data layer (ingestion, warehouse, dataset — whatever applies).
- **Learning target this week:** be able to explain in your own words: "what does this tool do, why did I pick it, and what would break if I removed it."
- **Friday demo #1:** Show the data flowing + a short explanation (3 min) of your tech stack choices.

### Week 2 (6 Jul – 10 Jul) — Core Build + Mid-Point Check-in
**Theme:** The "skinny" version of the product works end-to-end.
- Build: the core model / pipeline / dashboard / deployment.
- **Learning target:** document each technical decision in a short note (1 paragraph per decision). This is the start of your ADRs.
- **Friday demo #2:** End-to-end demo (5 min). Ugly is fine. Working is the bar.
- **Mid-program 1:1 with mentor** (Wed of this week). 30 min. Review progress, unblock, recalibrate if needed.

### Week 3 (13 Jul – 17 Jul) — Polish + Mini-Extension
**Theme:** Make it presentable. Add the **mini-extension** (a small, scoped addition that shows you can go beyond the minimum).
- Add: tests (1-2 are enough, just show you can), README polish, a simple "About" page.
- Build the **mini-extension** (see Doc 02 for what this looks like for your problem).
- **Learning target:** be able to onboard a friend to your repo in 15 minutes.
- **Friday demo #3:** Polished version of the product + the mini-extension demoed.

### Week 4 (20 Jul – 24 Jul) — Deploy + Document
**Theme:** Get it on the public internet. Write it up.
- Deploy: live URL on a free-tier cloud (or local + public tunnel).
- Write: README final, ADR set (3 ADRs minimum), a 3-min Loom walkthrough.
- Write: **your reflection piece** (the 1 written deliverable, see Doc 02 for spec).
- **Friday demo #4:** Live deployment demo + walkthrough.

### Week 5 (25-26 Jul) — Final Submission & Showcase
- **25 Jul (Sat):** Final submission (repo, deployed URL, README, Loom, reflection, resume bullets). Internal review.
- **26 Jul (Sun):** Public showcase. **All students present** (5 min each, segment-grouped). Certificates issued.

---

## 5. The 3-Output Rule

Every student ships exactly **3 outputs** by 26 July:

| # | Output | What it is | Why it matters |
|---|--------|-----------|----------------|
| 1 | **The Hero Project** | The working, deployed, documented project tied to your problem statement | Foundation of your 3rd year portfolio |
| 2 | **The Mini-Extension** | A small, scoped addition that goes beyond the minimum | Shows you can go deeper, not just wider |
| 3 | **The Reflection** | A 1000-1500 word written piece on what you learned, what you'd do differently, what to learn next | Trains the writing muscle + gives the next-internship team signal |

The **mini-extension** is what makes the 2nd year internship different from a 3rd year one. In the 3rd year, you'd ship 2-3 separate projects. Here, you ship 1 project + 1 well-scoped extension. The extension is what shows you can go beyond "I did the assignment."

Examples of good mini-extensions (you'll see the specific one for your problem in Doc 02):
- The Analytics project gets a "what-if simulator" added to the dashboard
- The DE project gets a streaming source added to the batch pipeline
- The ML project gets an A/B test comparison view added
- The DevOps project gets a chaos test added to the deployment

---

## 6. Weekly Cadence (The Rhythm)

| Day | Activity |
|-----|----------|
| Monday | Sprint planning: 3-5 tasks for the week in a GitHub Project board. |
| Tue–Thu | Build. Commit at least 3 times. Push. |
| Friday | Demo day. 3-5 min walkthrough. Get feedback. Record. |
| Saturday | Write: README updates, ADR drafts, learning notes, blog draft. |
| Sunday | Off. Rest. Read. Catch up. |

**Push code often.** A green commit graph in your GitHub profile is itself an artifact.

---

## 7. The "Push Every Day" Pledge

This is the single biggest differentiator between students who walk out of this internship ready for 3rd year and students who don't. Make a pledge to yourself: **commit and push something to your GitHub every day, even if it's just a README update or a one-line fix.** By 26 July, you'll have 30+ commits. That graph becomes a story: "this person works consistently." Recruiters read it.

---

## 8. What "Done" Looks Like at 2nd-Year Level

A done 2nd year project has:
- ✅ Code in Git, with regular commits
- ✅ README that explains the why, what, how, and how-to-run
- ✅ A deployed, live URL (free-tier is the standard)
- ✅ At least 1 test (a passing test is enough — you're learning the discipline)
- ✅ A 3-min Loom showing it working
- ✅ A reflection piece (1 written output)
- ✅ A clear path to extend it in 3rd year

It does NOT need:
- ❌ Multiple models compared
- ❌ A full eval harness
- ❌ ADRs for every decision
- ❌ A blog post
- ❌ Tests on every function
- ❌ A CI/CD pipeline (basic GitHub Actions deploy is enough)

Know the difference. This is the foundation. 3rd year is the production polish.

---

## 9. Mentorship — How It Works Here

The 2nd year batch gets **more mentor attention** than the 3rd year batch. Specifically:

- **1 mentor per 8-10 students** (vs 1:15+ for 3rd year)
- **Weekly 1:1 with your mentor** (scheduled Mon-Fri, 15 min). Non-negotiable.
- **Open office hours** every Wed + Fri, 4-6 PM. Walk in, no appointment.
- **Pair-debug sessions** if multiple students are stuck on similar issues (mentor will arrange).
- **Slack #help channel** monitored daily by at least 1 mentor.

**You are expected to use this.** A 2nd year student who finishes the internship without having had at least 4 mentor 1:1s is doing it wrong.

---

## 10. Help & Escalation

| Need | Where to go |
|------|-------------|
| Stuck on a concept | Segment mentor in 1:1, or office hours |
| Stuck on a build issue | Cohort Slack #help channel |
| Personal blocker | Internship coordinator — no judgement, no questions |
| Disagreement with mentor | Raise to internship lead, 24-hr turnaround |
| Want to switch problem statement | Allowed only in Week 1, with mentor sign-off |
| Failing behind, overwhelmed | **Tell your mentor by Wednesday of Week 2.** Don't hide. We will scope down or extend. |

---

## 11. What's NOT Allowed

- ❌ Group projects of any size
- ❌ Submitting work done before 22 June 2026
- ❌ Submitting a closed-source project
- ❌ "I couldn't deploy it" — there is a free tier for every cloud
- ❌ Skipping the reflection piece
- ❌ Going silent. If you're stuck, say so within 24 hours of being stuck
- ❌ Copy-pasting tutorials. The data, the analysis, the decisions must be yours

---

## 12. The Final Eval

You will be evaluated on **4 dimensions**, each equally weighted:

1. **Working Software (30%)** — Does it work? Is it deployed? Is it documented?
2. **Learning Depth (25%)** — Can you explain what you built and why? ADRs, design doc, mentor 1:1 conversations.
3. **Mini-Extension Quality (20%)** — Did you go beyond the minimum in a thoughtful way?
4. **Communication (25%)** — README quality, Loom, reflection piece, demo ability, resume bullets.

A clean, working, well-explained project with a thoughtful mini-extension will outscore a half-broken ambitious project. Don't overscope.

---

## 13. Beyond 26 July — The Extension Path

The point of this internship is what happens **after**. Each problem statement in Doc 02 has a **"3rd Year Extension Path"** section. This is your roadmap.

For example:
- Analytics student extends by adding a predictive churn model on top of the dashboard
- DE student extends by adding streaming, then by adding data contracts, then by adding a feature store
- ML student extends by adding a continuous-training loop, then by adding a feature store, then by adding a proper eval harness
- DevOps student extends by adding multi-tenancy, then by adding chaos engineering, then by adding a service mesh

By the time 3rd year internship rolls around, you should be **extending** the project you started here, not starting from zero. The 3rd year internship's "ship 3 artifacts" bar is much higher because you're standing on this foundation.

---

## 14. Documents in This Series

| Doc | Purpose |
|-----|---------|
| **01 — Workflow Guide (this doc)** | What to do, when, how. Process. |
| **02 — Technical & Business Problem Compendium** | Detailed scenarios, scope, tech direction for every problem statement + the **3rd year extension path**. |
| **03 — Deliverables Specification** | Exact weekly + milestone + final deliverables, format, evaluation. |

Read 01 fully before 22 June. Start skimming 02 by 20 June. Read 03 fully by 24 June.

---

**One last thing.** 2nd year internship is the easiest internship you'll ever do — in the sense that the bar is "real, working, deployed, with a reflection piece." 3rd year internship will demand 2-3 projects. After placements, the bar goes up again. **Don't peak too early. Use this month to build the foundation, the habits, and the confidence. The 3rd year internship will reward that.**

See you on 22 June.
