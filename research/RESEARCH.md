# Research for Catalyst AI (Vedashree)

**Branch:** `research`. You edit only `research/`. Your job: make sure Catalyst AI is **well-aimed, correctly checked and convincingly explained**, and keep the team honest about what is real.

**Product:** Catalyst AI, a **free** advisor for home-business owners (anyone who makes or sells something and takes orders through Instagram or WhatsApp) that gives them analytics to focus on **next month's sales**. First case study: Box Box (F1 merchandise). The loop: intake → diagnosis → advice → weekly follow-up. Main measure: **orders from strangers**.
**Read first:** `docs/DATASET.md`, `backend/BACKEND.md`, and the two team documents `AI_Business_Growth_Advisor_Project_Brief.docx` (the project brief) and `Lead_Qualification_Model.docx`. The two Word files are shared by the team and are **not in the repo**; ask Soham if you do not have them.

## 1. Decisions already made

| Decision | Choice |
|---|---|
| Direction | The Box Box project brief is final. The earlier "Solution Plan" PDF is dropped |
| Product name | **Catalyst AI** |
| Target user | Home-business owners of **any product**; working definition: first 50 to 500 orders, Instagram or WhatsApp, no ad budget, one to three people. Not for venture-backed startups, mid-size companies or established brands with an ad budget and an agency |
| Box Box's role | The first case study and demo, **not** the product's scope. A second sample (a home baker) shows it is not shirt-specific |
| Price | **Free for everyone** (no paid tier) |
| Language | English only for the prototype |
| Main measure | **Orders from strangers**, not friends |
| How diagnosis works | **Calculations decide, the AI explains.** The LLM reads messy input and explains; it never diagnoses or calculates |
| Lead model | Transparent points first (the team document `Lead_Qualification_Model.docx`); the public-data model is a learned challenger and sanity check |
| Data | Public datasets validate and calibrate; Box Box and the home baker are generated and labelled synthetic; real data is used if an owner shares it |

## 2. Why this user (for the pitch)

The brief compared segments and chose the one that **needs advice and knows it**:

| Segment | Verdict |
|---|---|
| Local offline businesses (shops, salons, clinics, restaurants, coaching) | Widest need, but data is on paper and owners rarely look for advice |
| Small manufacturers and job-shops | Most at stake per business, but hard to reach and slow to change |
| Kirana stores | **Dropped**: they feel a problem but not a need for an advisor, will not enter data, will not pay |
| Freelancers and solo service businesses | Real need, but a different product |
| Family businesses in a handover | Too few and too varied to start with |
| **Small e-commerce and home businesses** | **Chosen**: they feel the pain daily, already look for help, and their data is at least partly digital |

**Why one advisor for everyone does not work:** a kirana store and a medical store share basics (cash flow, stock, margins) but the decisions differ (pricing freedom vs MRP caps, slow stock vs expiry dates, light vs heavy rules). So we pick one type of business, make the advice good for it, and add types later on a shared core.

## 3. Competitors (from the project brief: verify every price and claim before it goes on a slide)

| Competitor | What it does | How it lags for our user |
|---|---|---|
| Shopify Sidekick | Built into the Shopify admin; diagnoses falling sales and suggests fixes | Needs a Shopify store and enough data |
| Triple Whale (Moby), Lebesgue | AI analysts for ad spend, attribution and profit | Paid plans (the brief cites about $219 a month, and $59 or $149); built for brands already running ads |
| Marketplace AI (Amazon, Flipkart, Meesho) | Seller-side AI tools | Only helps inside one marketplace |
| Agencies and consultants | Growth strategy for funded brands | Priced above what these owners earn |
| General chatbots | Free advice on anything | **The real competitor**: generic because it knows nothing about the owner's numbers |

**Our position:** we serve the stage *before* an owner is ready for those tools. We work from DMs, order sheets and an interview, focus on **reach** (not ad attribution), tie advice to the owner's own numbers with the evidence shown, and follow up every week, which a chatbot does not do. An owner who outgrows us is a success. Because we are free, the point is **specificity and follow-up**, not price.

## 4. Deliverables

Work in this order. Today the prototype must be shown; drafts by **4:00 PM**, finals by **4:45 PM**.

| # | Deliverable | File | Who uses it |
|---|---|---|---|
| R1 | **Licence check** for Online Shoppers and Bank Marketing (UCI's metadata lists none or "see page"), and a note that Olist is non-commercial. Say what we may do with each | `research/licences.md` | `docs/DATASET.md`, slides |
| R2 | **Lead-score check** (section 5): does the data support the points? | `research/lead_signals_check.md` | Soham (backend 1) |
| R3 | **Action library** (section 6): generic actions per bottleneck, reach partners, brand-risk wording | `research/action_library.md` | Ayush (backend 2) |
| R4 | **Competitor sheet** with every price and claim checked and sourced | `research/competitors.md` | Slides |
| R5 | **Demo script** for Box Box and the home baker (section 7) | `research/demo_script.md` | Whole team, video |
| R6 | **Claims ledger**: every claim we will make, its status (built / partial / scripted / planned) and evidence | `research/claims_ledger.md` | Slides, Q&A |
| R7 | **Q&A bank** with short, evidence-backed answers (section 8) | `research/qa_bank.md` | Whole team |
| R8 | **Slides outline** (5 to 7 slides) and the problem-and-solution text | `research/slides_outline.md`, `research/problem_solution.md` | Submission |
| R9 | **Golden set**: 20 to 30 test cases of diagnosis and lead scoring with expected answers | `research/golden_set.csv` | Both backends |
| R10 | **Founder interview guide** (section 9). The interviews themselves happen after the hackathon | `research/interview_guide.md` | Next stage |
| R11 | **Frontend needs** (section 10) | in this file | Kaushal |

If time is short, do R1, R3, R5, R6 first: they directly improve the build and the demo.

## 5. Lead-score check (R2)

The lead score is hand-set points (the team document `Lead_Qualification_Model.docx`). They are guesses, and the design says so. Your job is to check **directions** against public data and report honestly:

| Question | Public evidence | What to write |
|---|---|---|
| Does intent outweigh light interest (price question +40 vs like +5)? | Online Shoppers: sessions that saw pages with value convert at **56.3% vs 3.9%** | Supports the direction; say it is a different setting (shop sessions) |
| Does history raise the chance (bought before +30)? | Bank Marketing: previous success converts far higher than none (65% vs 9% across the full file) | Supports the direction |
| Does a long silence lower it (no activity in 30 days, -20)? | The Bank Marketing model's learned effect of days since contact is negative | Supports the direction; the size of 20 points is a guess |
| Do new people behave differently (stranger bonus +10)? | Online Shoppers: new visitors convert at **24.9% vs 13.9%** | Supports "different"; the bonus is a **growth choice**, not a measured effect, and must be described that way |

Also list **what is not supported**: the exact point values and thresholds, which only the owner's own outcomes can set (the weekly learning step). Do not overclaim.

## 6. Action library (R3)

A table per bottleneck (reach, conversion, margin, repeat orders, capacity). Each action: trigger, what to do, effort in minutes, a measurable target, the evidence that would justify it, risks, and whether it needs the owner's approval. **Generic** (works for any product), with Box Box and baker examples. Include:
- **Reach partners:** fan pages, creators, college and local communities; how to qualify them (audience match, location match, engagement not followers, past results, cost).
- **Timing:** using a demand window from the market-context calendar (race weekends for Box Box; festivals for others).
- **Brand and IP risk wording:** a plain-language warning that protected names, logos or characters can lead to takedowns, "this is not legal advice".
- Actions must respect: **no ad budget**, one to three people, limited hours.

## 7. Demo script (R5), about 3 minutes

| Time | Beat |
|---|---|
| 0:00 to 0:25 | **Problem.** A home-business owner with real orders, stuck in their own circle, with no dashboard and no budget |
| 0:25 to 0:55 | **Intake.** Upload an order sheet and paste a few DMs; show repairs, the quality badge, and the source tag on every field |
| 0:55 to 1:30 | **Diagnosis.** One bottleneck named from the data, with the number, the source and the confidence; two runners-up; the stranger-orders chart |
| 1:30 to 2:05 | **Advice.** One to three actions for the week with evidence; the daily list of Hot, Warm and Cold leads with drafted replies; the brand-risk card |
| 2:05 to 2:40 | **Next month.** The projection with its range and basis, labelled an estimate |
| 2:40 to 3:10 | **Follow-up.** Switch to week 2 (a scripted, labelled replay): what was done, what changed, adjusted actions |
| 3:10 to 3:30 | **Thesis.** "Calculations decide, the AI explains. Free for every home-business owner." Then switch to the **home baker** to show it is not shirt-specific |

Keep a recorded fallback and cached LLM answers in case connectivity fails.

## 8. Q&A bank (R7): prepare short answers to

- Isn't this just a chatbot? (Our difference: advice tied to the owner's own numbers, evidence shown, a weekly follow-up.)
- Where is the AI? (Reading messy input and labelling intent; explaining results. Calculations decide what is wrong.)
- Why is it free, and how does it last? (Free for the prototype; sustainability is an open question, say so honestly.)
- Is the data real? (Public datasets validate the engine; the demo businesses are generated and labelled synthetic; real owner data is used if shared.)
- Why Olist, Online Retail II, Online Shoppers and Bank Marketing? (See `docs/DATASET.md`.)
- How do you know the lead score works? (Points are starting guesses; directions are supported by public data; the weekly step learns from outcomes.)
- What about privacy? (Pseudonymised before any LLM, per owner, deletable.)
- Doesn't friend or stranger rely on self-reporting? (Yes; the owner tags it. Say so.)
- What if the AI misreads a message? (The owner can correct a label.)
- Trademark risk with merchandise? (We flag it; not legal advice.)
- What would you build next? (Screenshots, voice interview, official Instagram and WhatsApp connections, the learned score.)

## 9. Founder interview guide (R10)

Interviews with 10 to 15 similar founders are the brief's way to confirm that "stuck in my own circle" is the common problem. **They happen after the hackathon.** Draft a guide: what they sell, how they take orders, how many orders so far, where buyers come from (friends vs strangers), what they already tried, how much time they have, what data they keep, what they would pay attention to weekly. No selling; just listening.

## 10. What the frontend must show (R11, for Kaushal)

The stranger-orders chart and share; the five bottlenecks with the one chosen and two runners-up; the **evidence card** (claim, number, source, confidence) on every finding; provenance badges (`exact` / `estimate` / `derived`) on every number; the daily lead list with Hot, Warm, Cold, Disqualified and drafted replies (preview only); next month's projection with its range, labelled an estimate; the brand-risk card; a weekly follow-up view; a switch between the demo businesses; a clear "demo data" badge. Mobile-first.

## 11. Risks (from the brief) to keep visible

- **Trademarks:** F1 names, teams, logos and drivers are protected; unlicensed merchandise risks takedowns as a brand grows. The advisor catches this kind of risk, as a flag.
- **Messy data:** orders live in DMs, UPI apps and sheets. Intake must work with that, or owners drop off.
- **One case is not proof:** Box Box shows the problem exists for one seller. The interviews are what confirm it is common.
- **Staying specific:** if the advice reads like a general chatbot's, there is no reason to use us.
- **Small numbers:** a seller has few leads and few orders, so early rates swing; decisions wait for several weeks of data.
- **Willingness to pay** is not a risk here: the product is free. Sustainability beyond the hackathon is an open question.

## 12. Definition of done

- Each deliverable exists, is accurate and is cross-checked against what is built.
- Every slide claim appears in the claims ledger with its evidence; AI-generated or third-party figures were verified.
- The team can answer the Q&A bank without notes.
- Nothing is called measured that is a scenario assumption, and nothing synthetic is called real.
