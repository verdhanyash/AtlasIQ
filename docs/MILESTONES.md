# Deliverables Specification — 2nd Year Batch (B.Tech CSE-AIDE)

**Duration:** 22 June 2026 → 26 July 2026 (5 weeks)
**Mode:** Individual work. No grouping.
**Companion to:** 01_Workflow_Guide.md, 02_Technical_Problem_Compendium.md

---

## The Big Idea

This internship is a **foundation, not a final product**. The deliverables are deliberately lighter than the 3rd year batch — but they are still **structured, dated, and non-negotiable.** The goal is to build the habits, the tools, and the confidence that will make 3rd year internship (and placements) go well.

Every student — regardless of segment — submits the **same shape** of deliverables. Same rhythm, same format, same evaluation. The **content** is segment-specific (see Doc 02).

---

## The Three Categories of Deliverables

| Category | Count | Weight | What it shows |
|----------|-------|--------|---------------|
| **Weekly Deliverables** | 4 weekly submissions | 35% | Consistent execution, learning in public |
| **Milestone Deliverables** | 2 major submissions | 50% | Working software, mini-extension, communication |
| **Final Deliverables** | 1 final submission + showcase | 15% | Polish, presence, reflection |

Plus **2 mandatory soft deliverables** (not graded but required to pass):
- The **Certificate Eligibility Check** (you must hit a minimum bar)
- The **3rd Year Roadmap** (a personal artifact, not graded — but it's the most important thing you'll make)

---

# PART 1 — WEEKLY DELIVERABLES (4 weeks × 1 submission)

Every **Saturday, 11:59 PM IST**, you submit a weekly deliverable. Format: a **single GitHub Issue** in your project repo, titled `Week N Submission — <your name> — <problem code>`, with a checklist completed.

These are smaller and more forgiving than the 3rd year batch's. Missing one is a -3% on your final grade.

---

## Week 1 (Due Sat 4 July 2026, 11:59 PM)

**Theme:** Foundation laid. Repo alive. Data flowing. Mentor relationship started.

### Required in the GitHub Issue

- [ ] **Repo created and public.** Link.
- [ ] **README.md** with: project name, one-line description, problem-statement code, segment name, your name, "what I learned this week" section.
- [ ] **Initial Design Doc (1 page)** — final version, after mentor review. Embedded as `docs/design_doc.md` or linked.
- [ ] **Tech stack table.** Component | Choice | Why (one line).
- [ ] **Data layer working.** A screenshot or terminal output showing data ingested + queried.
- [ ] **At least 5 GitHub commits** on the main branch.
- [ ] **A "What I learned" note** (3-5 bullet points). Example: "Docker volumes work like X. I used to think they were the same as bind mounts. Now I get it."
- [ ] **One-pager status** at the end of the issue:
  - What's done: …
  - What's stuck: …
  - 3 goals for next week: …
  - One thing I'd like help from my mentor on: …

### What "done" looks like
Your mentor can read this issue in 5 minutes and know exactly where you are.

---

## Week 2 (Due Sat 11 July 2026, 11:59 PM)

**Theme:** End-to-end "skinny" version of the product works. Ugly is fine. Working is the bar.

### Required in the GitHub Issue

- [ ] **End-to-end demo.** Screenshot or 3-min screen recording of the full product working on a small slice.
- [ ] **Updated README** (the "What I learned" section has grown).
- [ ] **First ADR (Architecture Decision Record).** Use this format:
  ```
  # ADR-001: <Title>
  ## Context
  <what we're deciding and why>
  ## Decision
  <what we chose>
  ## Consequences
  <trade-offs, both positive and negative>
  ## Alternatives considered
  <what we rejected and why>
  ```
- [ ] **At least 10 GitHub commits** total on main.
- [ ] **A "What surprised me" note** (2-3 sentences). Real learning, not fluff.
- [ ] **Status one-pager** (same format as Week 1).
- [ ] **Mid-program 1:1 with mentor** completed (schedule via form). 15-30 min.

### What "done" looks like
You can show this to a friend outside LPU and they'd say "ok I roughly get it."

---

## Week 3 (Due Sat 18 July 2026, 11:59 PM)

**Theme:** Mini-extension built. Polish started.

### Required in the GitHub Issue

- [ ] **Mini-extension demo.** Screenshot or screen recording showing the mini-extension working (see Doc 02 for what this is for your problem).
- [ ] **At least 1 test** added. Doesn't matter what it tests — a passing test is the bar. Screenshot of the test passing.
- [ ] **README polished.** A reviewer can clone → set up → run in <20 min (yes, 5 more than the 3rd year batch — this is OK).
- [ ] **2 more ADRs** added (total 3 now).
- [ ] **At least 15 GitHub commits** total on main.
- [ ] **A "What I'd do differently" note** (2-3 sentences). Show self-awareness.
- [ ] **Status one-pager.**

### What "done" looks like
You can onboard a friend to your repo in 15 minutes. They'd run it, see the mini-extension, and say "cool, what's next?"

---

## Week 4 (Due Sat 25 July 2026, 11:59 PM)

**Theme:** Deployed. Documented. Recorded. Reflected.

### Required in the GitHub Issue

- [ ] **Live deployment URL.** A real, working URL.
- [ ] **3-min Loom walkthrough** of the deployed product. Public or unlisted.
- [ ] **All 3 ADRs finalised.** (Bonus: add a 4th — encouraged but not required.)
- [ ] **At least 20 GitHub commits** total on main.
- [ ] **Reflection piece** (1 written deliverable) — draft submitted, see "Reflection Spec" below.
- [ ] **Resume bullets draft.** 2-3 bullets, in "Action verb + tech + outcome" format.
- [ ] **Status one-pager.**

### What "done" looks like
A 1st-year student can clone your repo, see the live URL, watch the Loom, and understand the project. They could also imagine extending it next year.

---

# PART 2 — MILESTONE DELIVERABLES (2 major submissions)

These are graded more heavily than the 3rd year batch because they're your **foundation**. Submit via a **GitHub Release** (tagged `v1.0-m1` and `v1.0-m2`) with the assets in the repo.

---

## MILESTONE 1 — The "Alpha" Build (Due Sun 19 July 2026, 11:59 PM)

**Theme:** "If a friend cloned this right now, the core would work and they'd learn something from it."

### What to submit (GitHub Release `v1.0-m1`)

| # | Asset | Format | Notes |
|---|-------|--------|-------|
| 1 | **Public GitHub repo** | URL | All code, clean history, regular commits |
| 2 | **README.md** | Markdown in repo root | See "README Standard" below |
| 3 | **Architecture diagram** | PNG/SVG in `/docs` | Hand-drawn is fine if clean. C4 Level 1 or equivalent. |
| 4 | **Demo video (3-5 min)** | Loom link in README | Walk through the deployed product, narrate as you would to a peer |
| 5 | **At least 1 test** | In repo, passing | Show you understand the discipline |
| 6 | **ADR set** | `/docs/adr/` | 3 ADRs minimum |
| 7 | **Live deployment URL** | In README | Must be live and reachable at submission |
| 8 | **Mini-extension shipped** | In repo + demoed in Loom | The "going beyond the minimum" piece |

### README Standard (enforced)
A reviewer must be able to go from `git clone` → running product in 20 minutes. Mandatory sections:

```
1. Project Title + 1-line tagline
2. Demo (Loom embed + live URL)
3. Problem statement (1-2 paragraphs)
4. Architecture diagram
5. Tech stack (table)
6. Quickstart
   - Prerequisites
   - Install
   - Run
   - Test
7. Data sources
8. ADRs (link to /docs/adr/)
9. Mini-extension (what + why)
10. Known limitations
11. What I'd do in 3rd year (link to 3rd year roadmap)
12. License + Acknowledgements
```

### Evaluation rubric (Milestone 1)

| Dimension | Weight | What "5/5" looks like |
|-----------|--------|----------------------|
| Working software | 35% | It works end-to-end, deployed, mini-extension done |
| Engineering hygiene | 25% | Repo clean, README usable, tests present, ADRs thoughtful |
| Learning depth | 20% | You can explain your decisions, not just describe them |
| Communication | 20% | Loom is clear, README is honest, code has intent |

---

## MILESTONE 2 — The "Final" Build (Due Sat 25 July 2026, 11:59 PM)

**Theme:** "I'd put this on my resume for 3rd year internship applications, and I'd be honest about what it is."

### What to submit (GitHub Release `v1.0-final`)

Everything from Milestone 1, **plus:**

| # | Asset | Format | Notes |
|---|-------|--------|-------|
| 9 | **Reflection Piece** | `reflection.md` in `/docs` | 1000-1500 words. See "Reflection Spec" below |
| 10 | **3rd Year Roadmap** | `roadmap_3rd_year.md` in `/docs` | 6-12 month plan. See "Roadmap Spec" below |
| 11 | **Resume bullets** | `resume_bullets.md` in `/docs` | 2-3 polished bullets |
| 12 | **5 Q&A pairs** | `mock_interview.md` in `/docs` | 5 questions a 3rd-year internship interviewer might ask, with your answers |
| 13 | **Optional: Postmortem** | `postmortem.md` in `/docs` | 1 real bug or issue you hit and how you solved it. High-credit bonus. |

### Reflection Spec (1000-1500 words)

This is the **written centrepiece** of the 2nd year internship. It is also the most important writing you'll do this summer. Use this structure:

**Section 1: What I Built (200-300 words)**
- One paragraph: what the project is, what problem it solves, who it's for.
- One paragraph: what the mini-extension is and why I chose to add it.

**Section 2: What I Learned About the Tools (300-400 words)**
- The 3-4 tools/frameworks you used. For each: what it actually does (not the marketing description), what surprised you, what you'd tell a friend who's about to learn it.
- Honest, not promotional.

**Section 3: What I Learned About Myself (300-400 words)**
- What was harder than expected? What was easier?
- What kind of work did you enjoy most (modelling, building UI, writing tests, deploying, debugging)?
- What kind of work did you hate?
- Did you stick to the schedule or did you procrastinate? What does that tell you?

**Section 4: What I'd Do Differently (200-300 words)**
- If you started over, what would change?
- What do you wish your mentor had told you on Day 1?

**Section 5: What's Next — The 3rd Year Plan (200-300 words)**
- High-level: how this project becomes the seed of your 3rd year portfolio.
- This sets up the Roadmap deliverable below.

**Tone:** honest, not promotional. Write like you're writing to a future you who is going to read this in 6 months. This is for YOU, not for the grader.

### 3rd Year Roadmap Spec (1 page)

A concrete plan for how you'll **extend this project through 3rd year.** Not vague goals — specific features, specific months, specific tools.

Use this template:

```
# <Project Name> — 3rd Year Extension Roadmap

## What this project is today (2-3 lines)

## The arc: where this could be by 3rd year internship (May 2027)
<1 paragraph>

## 3rd Year Semester Plan (Aug 2026 - Dec 2026)

### Milestone 1 (Aug-Sep 2026): <Name>
- What I'll add: ...
- Tools I'll learn: ...
- Time commitment: ... hours/week
- Done looks like: ...

### Milestone 2 (Oct-Nov 2026): <Name>
- What I'll add: ...
- Tools I'll learn: ...
- Time commitment: ... hours/week
- Done looks like: ...

### Milestone 3 (Nov-Dec 2026): <Name>
- What I'll add: ...
- Tools I'll learn: ...
- Time commitment: ... hours/week
- Done looks like: ...

## 3rd Year Internship Plan (Jun-Jul 2027)
<1 paragraph: which 3rd year internship problem statement this becomes>

## What I'll need from the placement / mentor ecosystem
<resources, mentors, courses, communities>

## Risks & open questions
<what could go wrong, what I don't know yet>
```

### Evaluation rubric (Milestone 2)

| Dimension | Weight | What's new vs M1 |
|-----------|--------|------------------|
| Working software | 25% | Same as M1, but the polish matters more |
| Engineering hygiene | 20% | Same as M1 |
| Learning depth | 25% | The reflection + roadmap show real thinking |
| Communication | 30% | **Upweighted** — writing is the focus |

---

# PART 3 — FINAL SUBMISSION (Due Sun 26 July 2026, 11:59 PM)

### What to submit

| # | Asset | Format |
|---|-------|--------|
| 1 | **Final GitHub Release** `v1.0-showcase` | All of M2 + any polish |
| 2 | **Final Loom (2 min)** | The "what I built" elevator pitch. Friendly, not formal. |
| 3 | **Updated resume** | `resume_final.md` + a PDF version. The project is on the top line. |
| 4 | **Self-evaluation form** | Google Form. 10 questions, 10 min. |
| 5 | **Showcase slide (1 slide)** | PNG or PDF, used in the public showcase |
| 6 | **Updated 3rd Year Roadmap** | `roadmap_3rd_year_final.md` — incorporate any feedback from M2 review |

### Self-evaluation form (preview)

You'll be asked:
1. Segment chosen, problem chosen, why.
2. What tool/concept felt like a breakthrough this month.
3. What was the hardest week and why.
4. Rate your comfort (1-5) on: SQL, Python, Git, Docker, the core tech of your segment, the cloud platform you used, written communication.
5. What would you build next if you had 2 more weeks.
6. Which 3rd year internship segment are you now best positioned for?
7. Which 2-3 companies would you apply to first, for a 3rd year internship or pre-placement?
8. The 30-day post-internship plan: what you'll do in the next 30 days to keep the momentum.
9. (Optional) Anything you want the internship lead to know.

---

# PART 4 — MANDATORY (BUT UNGRADED) CHECKS

## Certificate Eligibility

To receive the **internship certificate**, all of the following must be true:

- [ ] All 4 weekly deliverables submitted (or accepted late per policy)
- [ ] Milestone 1 submitted (graded)
- [ ] Milestone 2 submitted (graded)
- [ ] Final submission made (graded)
- [ ] You have NOT submitted any work that was not done during 22 June – 26 July 2026
- [ ] Your repo is public OR shared with a designated reviewer with written explanation
- [ ] You attended at least 3 of 4 Friday demos (or watched the recordings and submitted a 1-paragraph summary each)
- [ ] You completed at least 2 mentor 1:1s during the 5 weeks
- [ ] The reflection piece is submitted (this is a hard requirement)

The certificate is **segment-specific**, e.g.:
- *Certificate of Internship in Foundations of Analytics Engineering*
- *Certificate of Internship in Foundations of Data Engineering*
- *Certificate of Internship in Foundations of Applied Machine Learning*
- *Certificate of Internship in Foundations of Cloud & DevOps*

A generic "Internship Completion" certificate is **not** issued. The segment title intentionally uses the word **"Foundations"** — distinguishing it from the 3rd year batch's **"Applied"** certificates.

---

## 3rd Year Roadmap (Not Graded, But Mandatory for Pass)

Same as the roadmap in Milestone 2, but **the final, post-feedback version is what gets archived.** This becomes:

1. Your north-star document for the next 12 months
2. A reference your 3rd year internship lead can read to understand where you started
3. A piece of evidence in 3rd year internship applications (some students include it as a portfolio artifact)

This is the most important thing you make this month. Treat it that way.

---

# Submission Logistics

## Where to submit

| Deliverable | Submission channel |
|-------------|---------------------|
| Weekly deliverables | GitHub Issue in your project repo (issue template will be provided) |
| Milestone 1 | GitHub Release `v1.0-m1` + form |
| Milestone 2 | GitHub Release `v1.0-final` + form |
| Final | GitHub Release `v1.0-showcase` + form |
| All forms | Google Forms (links shared Day 1) |

## Deadlines (consolidated)

| Date | What |
|------|------|
| 18 Jun, 11:59 PM | Pre-work (Python + Git refresher) released |
| 21 Jun, 11:59 PM | Pre-work submitted |
| 24 Jun, 11:59 PM | Initial Design Doc (1 page) |
| 26 Jun, 11:59 PM | Final architecture + tech stack sign-off |
| 4 Jul, 11:59 PM | Week 1 submission |
| 11 Jul, 11:59 PM | Week 2 submission (+ mid-program 1:1) |
| 18 Jul, 11:59 PM | Week 3 submission |
| 19 Jul, 11:59 PM | **Milestone 1 (Alpha)** |
| 25 Jul, 11:59 PM | Week 4 submission |
| 25 Jul, 11:59 PM | **Milestone 2 (Final)** |
| 26 Jul, 11:59 PM | **Final Submission + Showcase** |

**Late policy:** -10% per day, max 3 days. After 3 days, the submission is not accepted for grading (counts as missed for certificate eligibility). Extensions granted only for documented emergencies, via internship lead.

**Note on the 2nd year batch being more forgiving:** the 3rd year batch has the same late policy. The 2nd year batch gets the same grace because you have less prior context, not because the bar is lower in absolute terms. The bar is **scoped to your level** — but missed is missed.

---

# The "If You're Stuck" Ladder

1. **Stuck for < 24 hours** → Search the cohort Slack, ask in #help, try the docs, try a tutorial.
2. **Stuck for 24-48 hours** → Open a "Help Request" GitHub Issue in your repo. Mentor responds within 24 working hours.
3. **Stuck for > 48 hours** → Use the weekly 1:1 with your segment mentor. This is exactly what it's for.
4. **Stuck for > 1 week** → Reach out to the internship lead. We will scope down or pivot.
5. **Falling behind, overwhelmed, personal issues** → Tell your mentor by Wednesday of Week 2. **Do not hide.** We will help.

Going silent is the only failure mode. Stuck-and-asking is fine. Stuck-and-quiet is not.

---

# Evaluation Philosophy

We are not grading whether you "completed" the problem. We are grading whether you **built a working foundation** for 3rd year.

A "simple" project that's clean, working, deployed, and well-explained will outscore a "complex" project that's half-broken and undocumented.

**The 2nd year bias is:** working software beats ambitious software, learning in public beats hiding, asking for help beats silently failing, honesty beats polish.

You have 5 weeks. You have a mentor. You have peers. You can do this.

See you on 22 June.
