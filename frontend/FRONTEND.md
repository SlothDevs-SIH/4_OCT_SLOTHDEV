# Frontend: the Catalyst AI web app (Kaushal)

**Stack:** a mobile-first React web app (Next.js with TypeScript is fine), opened from a link, no install. Hosted on Vercel.
**Branch:** `frontend`. You edit only `frontend/`. **Contract:** [`../contracts/API_CONTRACT.md`](../contracts/API_CONTRACT.md) (v2 draft). **Research brief for what to show:** [`../research/RESEARCH.md`](../research/RESEARCH.md) section 10. **Data:** [`../docs/DATASET.md`](../docs/DATASET.md).

## 1. The product the UI must make obvious

Catalyst AI is a **free** advisor for **home-business owners** of any kind. The owner should be able to answer in ten seconds: *What is holding my business back? How do you know? What do I do this week? Who should I reply to today? What should I expect next month?*
Not a chatbot: **intake → diagnosis → advice → weekly follow-up.** Main measure: **orders from strangers**.

## 2. Build against mocks first

You are never blocked by the backends: write one API file (`lib/api.ts`) with a function per contract endpoint, and a mock mode that returns example JSON in the same shapes. Switching to the real API is a one-line setting (`NEXT_PUBLIC_API_BASE`). Until the gateway exists, proxy data paths to port 8001 and decision paths to port 8002. Write TypeScript types straight from the contract shapes (fact, lead, diagnosis, action, projection, follow-up).

## 3. Screens

| Screen | Shows |
|---|---|
| **Start** | Choose a demo business (Box Box or the home baker) or start your own; a clear "demo data" badge |
| **Intake** | Upload an order sheet (and costs, insights); paste DMs or comments; the short interview form; the import report: rows loaded, repaired, quarantined, the quality badge |
| **Dashboard** | The **stranger-orders** chart and share, week over week; the five bottleneck scores |
| **Diagnosis** | The one bottleneck, two runners-up, and the **evidence card** (claim, number, source, confidence) on each |
| **This week** | 1 to 3 actions with the evidence, effort, target and due date; mark done or skipped; draft previews; the brand-risk card ("not legal advice") |
| **Leads (daily list)** | Hot, Warm, Cold, Disqualified with the reasons behind each score and a drafted reply for each Hot lead (**preview only, nothing is ever sent**); the owner can tag friend or stranger and correct an intent label |
| **Next month** | The projection with its range and basis, labelled an **estimate** |
| **Follow-up** | What was done, what changed, adjusted actions; the week selector (week 1 to 4, scripted replay in the demo) |
| **Data sources** | The public datasets behind the numbers (from `/public-data`) |

## 4. UX rules

- **Trust first:** show what we know, what we inferred, how sure we are. Use "estimate", "expected range", "observational". Provenance badges (`exact`, `estimate`, `derived`) on every number.
- Never present generated data as real; never hardcode numbers in components; every number comes from the API.
- Loading, empty, error and "coming soon" (501) states on every screen.
- Mobile first; keyboard navigable; colour is never the only signal (contrast at least 4.5:1).
- English only for the prototype.
- The demo path must work without the network: keep mocks and a recorded fallback.

## 5. Demo path to keep working (about 3 minutes)

Start (Box Box) → intake (upload, paste DMs, show repairs and the badge) → dashboard → diagnosis (the evidence card) → this week's actions and the brand-risk card → daily lead list with drafted replies → next month → switch to week 2 and show the follow-up → switch to the **home baker** to show it is not shirt-specific. Rehearse this exact path on the deployed build; the demo script is in `research/RESEARCH.md` section 7.

## 6. Stages today

| Stage | Build | Connects to |
|---|---|---|
| F0 | Setup, layout, API file, mock mode, badges, states | – |
| F1 | Start, intake and import report | backend 1 (intake endpoints are built) |
| F2 | Dashboard and diagnosis on mocks | backend 1 facts and backend 2 diagnosis |
| F3 | This week's actions, daily lead list, drafts, risk card | backend 2 |
| F4 | Next month, follow-up, data sources | backend 1 and 2 |
| Final | Full-stack integration on `fullstack-integration`, polish, first public deploy | the gateway |

If a backend stage slips, keep building on mocks. **Working, public prototype by 5:00 PM.**

## 7. Definition of done

- Every screen works on mocks and on the real API; no hardcoded numbers; types match the contract.
- Loading, empty and error states exist; no unhandled errors on the demo path.
- The deployed link works on a phone and in an incognito window.
- Nothing synthetic is labelled real.
