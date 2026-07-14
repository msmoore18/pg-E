# Lazy S Ranch — PG&E Electric Usage Dashboard

**Current approach (Option C):** manual Green Button CSV exports from your
PG&E account, dropped into this repo, auto-processed into a Chart.js
dashboard on GitHub Pages. No PG&E API registration, no server, no SSL
cert. Full API automation is possible later — see "Upgrading later" below.

## ⚠️ Before you publish this anywhere: keep the repo private

Your Green Button CSVs contain your account holder name, PG&E account
number, and property addresses. The dashboard itself only shows
usage/cost numbers (no PII), but the **raw CSVs live in the repo**, so:

- Make the GitHub repo **private**.
- GitHub Pages from a private repo requires GitHub Pro/Team/Enterprise —
  or use Cloudflare Pages with Access (the same pattern you'd already
  looked at for the harvest dashboard) if you want it on a free plan
  with SSO-gated access instead.
- Don't commit CSVs to a public repo, even temporarily.

## How to get a Green Button export

1. Log into your PG&E account (myaccount.pge.com).
2. For each Service ID: **Energy Usage Details** → scroll to the bottom →
   click the **Green Button** icon → **Download my Data**.
3. Choose the date range you want and download. You'll get one CSV per
   Service ID.

You have 19 Service IDs on the Lazy S account — for a full picture you'd
eventually want an export per service, though starting with a handful
(pumps, wells you care most about) and adding the rest over time works
fine too.

## Weekly (or whenever) routine

1. Download fresh CSVs from PG&E for whichever services you want updated.
2. Drop them into `data/raw/` in the repo (GitHub's web "Add file → Upload
   files" works fine, or `git add`/`push` if you're comfortable with that).
3. GitHub Actions automatically parses them and updates the dashboard —
   no need to run anything yourself.

## Naming your meters

PG&E's export only identifies each meter as "Service 1", "Service 2", etc.
— it doesn't know you call it the "Northern Blocks Irrigation Pump." To fix
that:

1. Open a raw CSV in `data/raw/` and check its `Address` field (a legal
   land description or street address) to figure out which physical meter
   it is.
2. Add the friendly name to `data/meter_labels.json`, e.g.:
   ```json
   { "Service 1": "Northern Blocks Irrigation Pump" }
   ```
3. Push the change — the workflow re-runs and the dashboard picks up the
   new name automatically. Naming a meter "Pump", "Well", or "Wind
   Machine" (anywhere in the name) also groups it under the right category
   on the dashboard automatically.

Until a service is labeled, it still shows up on the dashboard fully
charted — just grouped under "Unlabeled Meters."

## Turn on GitHub Pages

Repo → Settings → Pages → deploy from `/docs` on `main`. Dashboard will be
live at `https://<username>.github.io/lazys-pge-dashboard/` (restrict
access per the privacy note above).

## What this gives you vs. what it can't

- **Can:** hourly or 15-minute interval usage per meter, cost, category
  rollups, trend charts — refreshed whenever you drop in a new export.
- **Can't:** true automatic daily refresh without you doing anything, or
  real-time/live wattage like the Emporia Vue at the house. This is
  "semi-automated" — the processing is automatic, the data pull isn't.

## Upgrading later to full API automation

`future-api-upgrade/fetch_pge_data.py` has a working start on pulling data
directly from PG&E's Share My Data API instead of manual CSV exports. That
path needs:

- Registering as a PG&E Self-Access User at sharemydata.pge.com
- A CA-issued SSL certificate (not self-signed — DigiCert, GoDaddy,
  Sectigo, etc.) for mutual TLS
- An always-on server (small VPS, or GoDaddy hosting beyond the Website
  Builder plan) to receive PG&E's notifications

Or, skip running your own server entirely by using a paid aggregator like
UtilityAPI, which has already done PG&E's registration and server setup —
you'd authorize them and pull clean JSON from their API instead.
