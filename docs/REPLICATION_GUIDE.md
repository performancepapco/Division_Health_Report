# Division Health Card — full replication guide for a new circle

This is one sequential document covering everything needed to stand up
this entire system — data pipeline, dashboard, intake Form, and hosting —
for a **different postal circle**, starting from nothing. It consolidates
everything in `docs/*.md`, plus the parts that were done as one-time
engineering work the first time around (Phases 0–2), which a new circle
needs to redo too since the codebase itself doesn't ship pre-wired for a
specific circle's data.

**Read this top to bottom the first time.** The order matters — several
later steps depend on accounts/values created in earlier ones. Steps are
grouped into parts; each part names exactly what you'll have at the end
of it.

---

## Part 0 — What you're building

A pipeline that turns monthly Excel/CSV reports from individual post
offices into a public (or access-gated) web dashboard, automatically:

```
Branch staff → Google Form → Apps Script → Google Drive (DHCUploads/)
    → GitHub Action (validate → build → commit) → Cloudflare Pages
    → your custom domain
```

Nothing here is AP-Circle-specific in the *code* — everything circle-
specific is either (a) one YAML config file, (b) a handful of values in
one Apps Script file, or (c) external account setup (Drive, GitHub,
Cloudflare, domain). Part 3 below is the only part that touches code.

---

## Part 1 — Prerequisites & subscriptions (get these first)

None of these cost money at the tier this system needs, but each is a
separate account/signup:

| # | What | Why | Cost |
|---|---|---|---|
| 1 | A Google account | Owns Drive (`DHCUploads`), the intake Form, Apps Script | Free |
| 2 | A Google Cloud project (under the same Google account) | Hosts the service account that lets GitHub Actions read Drive | Free |
| 3 | A GitHub account | Hosts the code + runs the automation (GitHub Actions) | Free tier is enough |
| 4 | A Cloudflare account | Hosts the live dashboard (Cloudflare Pages), DNS, optional login gate (Access) | Free plan is enough |
| 5 | A domain name (any registrar — GoDaddy, Namecheap, etc.) | The public URL people will actually use | Registrar's price (~$10–15/yr typically) |
| 6 | Node.js installed on whatever machine does the one-time Cloudflare setup | Needed once, to run `wrangler` (Cloudflare's CLI) | Free |
| 7 | Python 3.12+ installed on whatever machine builds/tests the pipeline locally | Needed to run the pipeline scripts locally before/while setting up | Free |

Nothing here requires a paid GitHub or Cloudflare plan. If the repo ever
needs to go **private**, GitHub Pro is required to host GitHub Pages on a
private repo — but this system doesn't use GitHub Pages at all (Cloudflare
Pages instead), so that's not a constraint either way.

---

## Part 2 — Get the code

**Recommendation: one GitHub repo per circle**, not one shared repo for
multiple circles. Each circle gets its own data, its own Drive folder, its
own domain, its own access control — sharing a repo would mean sharing all
of that too.

1. On GitHub, create a **new repository** for the new circle (e.g.
   `<circle-name>-health-card`).
2. Copy this repo's code into it. Simplest way: clone this repo locally,
   remove its `.git` folder, `git init` fresh, add the new repo as
   `origin`, commit, push. (Using GitHub's "Use this template" button
   works too if this repo is marked as a template.)
3. **Do not copy `data/`, `uploads/`, or any circle-specific committed
   data** — start those empty; Part 3 explains what each new circle needs
   in their place.

You now have a copy of the codebase, disconnected from the original
circle's history and data.

---

## Part 3 — Customize the code for this circle

This is the only part that touches code, and it's small: one YAML file,
one Excel roster, and a handful of constants in one Apps Script file.

### 3.1 — The master office roster

Every section (POSB, PLI, RPLI, Booking) reconciles against a master list
of every real office in the circle — which offices exist, their division,
sub-division, region, and office type (HPO/SPO/BPO). This has to come
from the new circle's own MIS/hierarchy data.

1. Get (or export) a spreadsheet listing every office with at minimum
   these columns: `office_id`, `office_name`, `office_type_code`,
   `division_name`, `sub_division_name`, `region_name`.
2. Save it as `uploads/Hierarchy_data.xlsx`, sheet named `Worksheet`
   (or update `pipeline_config.yaml`'s `circle.master_roster_sheet` to
   match whatever sheet name you actually use).
3. This file changes rarely (roster changes, not monthly activity) —
   it's deliberately **not** part of the monthly Form uploads.

### 3.2 — `pipeline_config.yaml`

Open this file and update:

- `circle.name` — the new circle's name (e.g. `"Telangana Circle"`).
- `circle.master_roster_file` / `circle.master_roster_sheet` — if you
  named things differently in 3.1.
- `sections.ecr.known_divisions` — the full list of division/RMS-unit
  names as they appear **verbatim** in that circle's ECR Excel export
  (this list is used to filter which rows count — get this exactly right
  or divisions will silently be dropped).
- `sections.ecr.circle_full_extra_rows` — the circle's own admin/regional/
  PSD row names that sit outside the 33-division sum (varies by circle —
  find these by opening a real ECR export and identifying which named
  rows aren't a division or RMS unit).

Everything else in this file (header/column specs, validation bands,
canonical filenames) describes the **shape** of MIS system exports, which
is standardized nationally — leave those as-is unless the new circle's
source reports genuinely have different column layouts (rare; if so,
compare a real file's headers against the relevant section's
`required_headers` and adjust to match).

### 3.3 — Regenerate `office_hierarchy.json`

Booking's derived views (`OFFICE_STATUS_BY_MONTH`, `SUBDIV_BOOKING`) use
`office_hierarchy.json` — a flattened `office_id → {name, type, division,
region}` map covering **every** office type (not just BPO/SPO/HPO, unlike
the roster in 3.1). If you have a hierarchy export with an
`office_type_code` column covering all types, generate this with a short
one-off script (see the shape read by `pipeline/sections/booking.py`'s
`load_hierarchy()`) — or, if 3.1's roster already covers every type your
circle has, just reuse the same source, filtered differently.

### 3.4 — Templates and dashboard branding

1. Run `python generate_templates.py` — regenerates `/templates/*` from
   the updated `pipeline_config.yaml`.
2. `index.html` has circle-specific display text (title, "AP Circle",
   division/region labels in various headings) — search for the old
   circle's name and update the visible text. This is cosmetic; it
   doesn't affect the pipeline.

### 3.5 — Prove it still works before going further

Before setting up any external services, rebuild one real month locally
with the new circle's real files and sanity-check the output:

```
pip install -r requirements.txt
python build_dataset.py --section ecr --month 2026-XX --input path/to/ECR.xlsx
python build_dataset.py --section posb --month 2026-XX --input path/to/POSB.xlsx
# ...repeat for pli, rpli, booking...
python assemble.py
python -m http.server
```

Open `http://localhost:8000` and confirm the dashboard renders real
numbers for the new circle. Don't proceed to Part 4 until this works —
everything after this point is wiring the same working pipeline up to
automated, hosted infrastructure.

---

## Part 4 — Google Drive

Full detail: `docs/DRIVE_SETUP.md` (steps are circle-agnostic, just
follow them as written). Summary:

1. Create a Google Cloud project.
2. Enable the Google Drive API.
3. Create a service account, generate a JSON key.
4. Create a `DHCUploads` folder in Drive, share it **Viewer** with the
   service account's email.
5. Note the JSON key content — needed in Part 5.

---

## Part 5 — GitHub repo secrets

Full detail: `docs/GITHUB_ACTIONS_SETUP.md`. On the **new** repo from
Part 2:

1. Add secret `GDRIVE_SA_KEY` = the full JSON key content from Part 4.
2. Set up a Gmail (or any SMTP-capable) address for uploader-error
   notifications: turn on 2-Step Verification, create an App Password,
   add secrets `GMAIL_ADDRESS` and `GMAIL_APP_PASSWORD`.
3. Leave `AUTO_PROMOTE` unset for now (manual production promotion is the
   safer default until you trust the pipeline in production).

`CLOUDFLARE_API_TOKEN` / `CLOUDFLARE_ACCOUNT_ID` come later, in Part 7.

---

## Part 6 — Google Form + Apps Script

Full detail: `docs/FORM_STRUCTURE.md` and `docs/APPS_SCRIPT_SETUP.md`.
Circle-specific parts to get right:

1. Build the Form exactly per `FORM_STRUCTURE.md`'s question
   titles/options — **except** the "Section" dropdown's options must
   match this circle's `pipeline_config.yaml` section **labels**
   exactly, and "Reporting Month" should cover this circle's own
   relevant fiscal year.
2. **Collect email addresses → Verified** — easy to miss (it was missed
   the first time this system was set up, and every submission silently
   failed with "unauthorized email: (none collected)" until caught). Test
   by opening the Form fresh — it must force a Google sign-in before
   showing any questions.
3. In `apps_script/Code.gs`, update for the new circle:
   - `ALLOWED_EMAILS` — the real uploader accounts for this circle.
   - `GITHUB_REPO` — the new repo's `owner/name`.
   - `SECTION_LABEL_TO_KEY` / `SECTION_CANONICAL_FILENAME` — must match
     `pipeline_config.yaml`'s section keys/labels/`canonical_filename`
     values exactly.
   - `MONTH_LABEL_TO_ISO` — this circle's fiscal year month list.
4. Create a fine-grained GitHub PAT scoped to **only** the new repo, with
   **Contents: Read and write** and **Actions: Read and write**. Getting
   either of these wrong produces an HTTP 403 "Resource not accessible by
   personal access token" on every dispatch attempt — a real issue hit
   during the first rollout; double-check both permissions explicitly
   before moving on, don't just create the token and assume it's right.
5. Store the PAT as Script Property `GITHUB_PAT`.
6. Wire up the **installable** trigger (`onFormSubmit`, "From form", "On
   form submit") — a function of this name does nothing on its own; it
   must be explicitly bound as a trigger, or nothing ever fires.
7. Test end to end: submit a real file → Apps Script Executions log shows
   `Accepted: ...` then `GitHub dispatch sent OK` → file lands in
   `DHCUploads/<month>/<canonical name>` → a workflow run appears on
   GitHub automatically.

**If you manually upload a replacement file to Drive instead of going
through the Form** (e.g. for testing): delete the old file first, don't
rely on drag-and-drop "replace" — Drive sometimes creates a renamed
duplicate (`Name (1).csv`) instead of overwriting, and the pipeline reads
by exact filename, so a stray duplicate silently means your edit is never
picked up.

---

## Part 7 — Domain + Cloudflare

Full detail: `docs/CLOUDFLARE_CUTOVER.md` — every step there is
circle-agnostic except the actual domain name; follow it in order,
substituting the new circle's domain everywhere `ehealthcard.in` appears,
and `dhc-staging`/`dhc-production` with whatever project names you choose
for this circle.

**One workflow bug already fixed in the code, worth knowing about if
you're comparing against an older copy:** `gitleaks-action` (secret
scanning) cannot run on `repository_dispatch` events at all — it errors
immediately with "The [repository_dispatch] event is not yet supported."
If it's embedded inside `pipeline.yml` in whatever copy you're working
from, every Form-triggered automatic run will fail before it even reaches
your data, while manual test runs (`workflow_dispatch`) look fine — which
is exactly what made this confusing to diagnose the first time. It should
already live in its own `secret-scan.yml` (triggered on `push` instead)
in this codebase; if not, split it out the same way before relying on
automatic dispatch-triggered runs.

**Access control decision:** decide up front whether this circle's
dashboard should be:
- **Public** — simplest, no login, appropriate if the data isn't
  sensitive or the audience is too large to maintain a list (this is
  what AP Circle ended up choosing, at 10,600+ offices).
- **Restricted to a specific list** — fine for a short, fixed set of
  viewers.
- **Restricted by email domain** — the best fit for "every employee, but
  nobody outside the organization," with zero per-person admin work.
  Recommended default at any real scale. `docs/CLOUDFLARE_CUTOVER.md` §11
  has the exact steps for this option.

---

## Part 8 — Go-live checklist

- [ ] Local build (Part 3.5) renders correctly with real data
- [ ] `DHCUploads` created and shared with the service account
- [ ] All GitHub secrets set (`GDRIVE_SA_KEY`, `GMAIL_ADDRESS`,
      `GMAIL_APP_PASSWORD`, `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`)
- [ ] Form built, email collection verified working (test by submitting
      without being signed in — it should be impossible)
- [ ] Apps Script deployed, trigger installed, one real end-to-end
      submission confirmed (Drive → dispatch → GitHub Action → staging)
- [ ] Domain live on Cloudflare, both Pages projects deployed
- [ ] Access control decision made and implemented (Part 7)
- [ ] `Promote to Production` tested at least once manually
- [ ] New URL communicated to everyone who needs it

## Part 9 — Ongoing operations

- **Day to day:** branches submit through the Form; the pipeline
  validates, builds, and deploys to staging automatically within
  seconds. A daily cron run (06:30 UTC / 12:00 IST) acts as a safety net
  in case a dispatch event is ever missed.
- **Promoting to production:** GitHub Actions tab → **Promote to
  Production** → **Run workflow**. This is manual by design (no native
  approval-gate on GitHub's Free plan for a private repo) — review
  staging first. Set the `AUTO_PROMOTE` repo variable to `true` later to
  skip this and go straight to production once you trust validation
  alone.
- **A validation failure never reaches the live site** — invalid uploads
  are rejected with a plain-language reason (emailed to the uploader if
  `GMAIL_*` secrets are set), and the last good data stays live.
- **Changing what a section validates/expects:** edit
  `pipeline_config.yaml` only — templates and validation both read from
  it, so they can't drift apart. Re-run `generate_templates.py`
  afterward and recirculate the updated template file to uploaders.

---

## Part 10 — If something breaks: real issues hit during the first rollout

Kept here because every one of these looked like a different kind of
failure at first and took real back-and-forth to diagnose:

1. **A GitHub Action run is green, but nothing changed on the dashboard.**
   Green only means "no validation errors" — it's also green when there
   was simply nothing new to build (e.g. wrong month selected on a manual
   run, or the file never actually reached `DHCUploads`). Check the run's
   Job Summary for "Rebuilt: ..." vs. "nothing to build," and check for a
   new "Update dashboard data" commit before assuming the data changed.
2. **Dispatch fails with HTTP 403 "Resource not accessible."** The PAT is
   missing `Contents: Read and write` or isn't scoped to the right repo —
   see Part 6, step 4. Editing the token's permissions in place usually
   works without needing to update the `GITHUB_PAT` Script Property again.
3. **Apps Script log shows "unauthorized email: (none collected)."** The
   Form's "Collect email addresses" isn't set to **Verified** — see
   Part 6, step 2.
4. **Automatic (dispatch-triggered) runs fail, but manual runs succeed.**
   Almost certainly the gitleaks/`repository_dispatch` issue — see Part 7.
5. **A file "uploaded properly" to Drive, but the pipeline never finds
   it.** Check whether it's sitting in the Form's own auto-generated
   attachment folder (`<Form name> (File responses)/...`) instead of
   `DHCUploads/<month>/<canonical name>` — that means Apps Script never
   successfully processed the submission (see issues 2–3 above for why).
6. **`ehealthcard.in`-equivalent loads without asking for login, but you
   expected it to be gated.** Cloudflare Access applications are scoped
   per-**hostname** — attaching a custom domain to a Pages project does
   **not** inherit the Access policy already set up on the project's
   `*.pages.dev` URL. Each hostname needs its own Access application.
7. **A Pages project's URL times out even though Access authentication
   succeeded (you got the PIN, it accepted it).** The project likely has
   zero deployments yet — `Promote to Production` doesn't build anything,
   it only deploys whatever the pipeline already committed; if production
   was never deployed to even once, there's nothing behind Access to
   serve. Check the project's Deployments tab.
