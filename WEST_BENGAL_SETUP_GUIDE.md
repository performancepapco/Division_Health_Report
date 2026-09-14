# Division Health Card — complete build guide for West Bengal Circle

**One self-contained document.** Everything needed to stand up this entire
system — data pipeline, dashboard, intake Form, automation, and hosting —
for West Bengal Circle, starting from nothing. You do not need any other
file to follow this; everything from the original `docs/*.md` set has been
folded in here.

Handed over from **AP Circle**, where this system has been running in
production since 2026 across 10,600+ offices.

**Read top to bottom the first time.** The order matters — later steps
depend on accounts and values created in earlier ones.

---

## Table of contents

- [Part 0 — What you're building](#part-0--what-youre-building)
- [Part 1 — Accounts and prerequisites](#part-1--accounts-and-prerequisites)
- [Part 2 — Get the code](#part-2--get-the-code)
- [Part 3 — Customize the code for West Bengal](#part-3--customize-the-code-for-west-bengal)
- [Part 4 — Google Drive + service account](#part-4--google-drive--service-account)
- [Part 5 — GitHub secrets and variables](#part-5--github-secrets-and-variables)
- [Part 6 — The intake Google Form](#part-6--the-intake-google-form)
- [Part 7 — Apps Script](#part-7--apps-script)
- [Part 8 — Domain and Cloudflare hosting](#part-8--domain-and-cloudflare-hosting)
- [Part 9 — Go-live checklist](#part-9--go-live-checklist)
- [Part 10 — Ongoing operations](#part-10--ongoing-operations)
- [Part 11 — Troubleshooting](#part-11--troubleshooting)
- [Appendix A — Repository map](#appendix-a--repository-map)
- [Appendix B — The seven sections](#appendix-b--the-seven-sections)
- [Appendix C — Data model](#appendix-c--data-model)
- [Appendix D — Known issue to fix before go-live](#appendix-d--known-issue-to-fix-before-go-live)

---

## Part 0 — What you're building

A pipeline that turns monthly Excel/CSV reports from individual post
offices into a web dashboard, automatically:

```
Branch staff
    │
    │  submits one file through a Google Form
    ▼
Google Form ──► Apps Script ──► Google Drive (DHCUploads/<month>/<canonical name>)
                     │
                     │  fires a GitHub repository_dispatch
                     ▼
              GitHub Actions  ──►  validate ──► build ──► commit data/
                     │                 │
                     │                 └─ on failure: email the uploader, deploy nothing
                     ▼
              Cloudflare Pages (staging)
                     │
                     │  manual "Promote to Production" (or automatic, one flag)
                     ▼
              Cloudflare Pages (production) ──► your custom domain
```

### The design principles worth knowing before you start

1. **A validation failure never reaches the live site.** Invalid uploads
   are rejected with a plain-language reason emailed back to the uploader,
   and the last good data stays live.
2. **`pipeline_config.yaml` is the single source of truth.** Both the blank
   templates handed to uploaders and the header checks that gate deployment
   read from it, so they cannot drift apart.
3. **Nothing in the *code* is circle-specific.** Everything specific to a
   circle is either one YAML file, one Excel roster, a handful of constants
   in one Apps Script file, or external account setup. Part 3 is the only
   part that touches code, and it is small.
4. **Only `index.html` and `data/` are ever deployed.** The pipeline
   source, raw uploaded Excel files, and config are never published.

### Recommendation: one repo per circle

Give West Bengal its **own GitHub repository**, not a shared one with AP.
Each circle has its own data, its own Drive folder, its own domain, and its
own access control — sharing a repo would mean sharing all of that too.

---

## Part 1 — Accounts and prerequisites

None of these cost money at the tier this system needs, but each is a
separate signup. Get all of them before starting Part 2.

| # | What | Why | Cost |
|---|---|---|---|
| 1 | A Google account | Owns Drive (`DHCUploads`), the intake Form, the Apps Script | Free |
| 2 | A Google Cloud project (same Google account) | Hosts the service account that lets GitHub Actions read Drive | Free |
| 3 | A GitHub account | Hosts the code and runs the automation | Free tier is enough |
| 4 | A Cloudflare account | Hosts the dashboard, DNS, optional login gate | Free plan is enough |
| 5 | A domain name (any registrar) | The URL people will actually use | ~₹800–1,500/yr typically |
| 6 | Node.js on the machine doing one-time Cloudflare setup | Needed once, to run `wrangler` | Free |
| 7 | Python 3.12+ on the machine that builds/tests locally | Runs the pipeline scripts | Free |

Nothing here requires a paid GitHub or Cloudflare plan. If the repo later
needs to go private, note that GitHub Pages on a private repo needs GitHub
Pro — but this system uses **Cloudflare Pages**, not GitHub Pages, so that
is not a constraint either way.

**Python dependencies** (installed in Part 3.7 via
`pip install -r requirements.txt`):

```
openpyxl>=3.1
pandas>=2.0
PyYAML>=6.0
google-api-python-client>=2.100
google-auth>=2.23
```

---

## Part 2 — Get the code

1. On GitHub, create a **new repository** for West Bengal, e.g.
   `west-bengal-health-card`.
2. Copy the AP repo's code into it. Simplest path: clone the AP repo
   locally, delete its `.git` folder, run `git init` fresh, add the new
   repo as `origin`, commit, push.
3. **Do not copy `data/`, `uploads/`, or `office_hierarchy.json`** — those
   are AP's committed data. Start them empty; Part 3 explains what West
   Bengal needs in their place.

You now have a copy of the codebase, disconnected from AP's history and
data.

---

## Part 3 — Customize the code for West Bengal

This is the only part that touches code: one YAML file, one Excel roster,
a JSON hierarchy file, and some display text.

### 3.1 — The master office roster

Every section (POSB, PLI, RPLI, Booking) reconciles against a master list
of every real office in the circle — which offices exist, their division,
sub-division, region, and office type. This must come from West Bengal's
own MIS/hierarchy data.

1. Export a spreadsheet listing every office with at minimum these
   columns: `office_id`, `office_name`, `office_type_code`,
   `division_name`, `sub_division_name`, `region_name`.
2. Save it as `uploads/Hierarchy_data.xlsx`, sheet named `Worksheet` (or
   update `circle.master_roster_sheet` in `pipeline_config.yaml` to match
   whatever sheet name you actually use).
3. This file changes rarely — roster changes, not monthly activity — so it
   is deliberately **not** part of the monthly Form uploads. You maintain
   it centrally.

### 3.2 — The office geography files (optional but recommended)

Static per-office location reference — pincode, latitude/longitude,
district, constituency, tribal-area flags. Also not a monthly upload.
AP received these split across two files, both keyed by `office_id` and
merged at load time. Configure under `circle:`:

- `office_geo_file` / `office_geo_sheet`
- `office_district_file` / `office_district_sheet`

If West Bengal has this data in a single file, point both at the same file.
If you do not have it at all, the dashboard's map and district views will
be limited but the rest of the system works.

**One column in this file matters beyond geography: `pli_id`.** It is the
insurance feeds' own office key — the PLI/RPLI detail sheets' "Office Code" —
and it is the only shared key between the master roster and those feeds.
`pipeline/derive/subdiv_bolookup.py` uses it to attribute each office's real
premium to that office. Without it, insurance falls back to matching on
(division, office name) and **splits policies and premium evenly across
same-named offices in a division**, so those offices show an average rather
than their own figures. In AP that fallback affected 455 offices until the
`pli_id` join was added, so make sure WB's geo export includes the column.

Where the master data's own `pli_id` is wrong — shared by two offices, or a
placeholder `0`/blank — corrections go in `pli_id_overrides.json` at the repo
root: an `applied` map of `office_id` → correct `pli_id`, plus a
`pending_upstream` map for corrections whose ID does not exist in any feed
yet (recorded, deliberately not applied). Delete AP's copy and start fresh;
an absent file simply means no corrections.

### 3.3 — `pipeline_config.yaml`

Open the file and update these keys:

| Key | What to set |
|---|---|
| `circle.name` | `"West Bengal Circle"` |
| `circle.master_roster_file` / `_sheet` | Match whatever you did in 3.1 |
| `circle.real_office_types` | Usually `["BPO", "SPO", "HPO"]` — leave as-is unless WB differs |
| `circle.office_geo_file` etc. | From 3.2 |
| `sections.ecr.known_divisions` | **Critical.** The full list of WB's division and RMS-unit names, spelled **verbatim** as they appear in WB's own ECR Excel export |
| `sections.ecr.circle_full_extra_rows` | WB's own admin/regional/PSD row names that sit outside the division sum |

> **Get `known_divisions` exactly right.** This list decides which rows
> count. A name that does not match character-for-character means that
> division is **silently dropped** from every total — no error, just wrong
> numbers. Open a real WB ECR export and copy the names from it directly;
> do not retype them from memory. AP's list has 33 entries (29 divisions
> plus `RMS AG`, `RMS TP`, `RMS V`, `RMS Y`); West Bengal's will differ.

> **`circle_full_extra_rows`** is how the circle-wide consolidated figure
> (`CIRCLE_FULL`) is built: it sums the known divisions **plus** these
> extra rows, which the per-division view deliberately excludes. Find them
> by opening a real ECR export and identifying every named row that is
> neither a division nor an RMS unit — AP's are the circle office itself,
> a GM (Finance) row, a PSD, and three regional rows.

**Everything else in this file — header specs, column positions,
validation bands, canonical filenames — describes the shape of national
MIS system exports, which are standardized across circles. Leave those
as-is** unless a real WB file genuinely has a different column layout. If
it does, compare the real file's headers against that section's
`required_headers` and adjust to match.

### 3.4 — Regenerate `office_hierarchy.json`

Booking's derived views (`OFFICE_STATUS_BY_MONTH`, `SUBDIV_BOOKING`) read
`office_hierarchy.json` — a flattened `office_id → {name, type, division,
region}` map covering **every** office type, not just BPO/SPO/HPO like the
roster in 3.1.

Generate it from a WB hierarchy export that includes an `office_type_code`
column covering all types. The exact shape expected is defined by
`load_hierarchy()` in `pipeline/sections/booking.py` — read that function
and write a short one-off script to match. If your 3.1 roster already
covers every office type WB has, you can reuse the same source file,
filtered differently.

### 3.5 — Regenerate the templates

```bash
python generate_templates.py
```

This rewrites `/templates/*` from your updated `pipeline_config.yaml`.
These are the blank files you hand to uploaders. Regenerate them any time
you change the config, and recirculate them.

### 3.6 — Dashboard branding

`index.html` contains display text naming the circle — the page title,
"AP Circle" in various headings, division and region labels. Search for
the old circle's name and replace the visible text. This is cosmetic and
does not affect the pipeline.

### 3.7 — Prove it works locally before going further

Before setting up any external service, rebuild one real month with real
WB files and sanity-check the output:

```bash
pip install -r requirements.txt

python build_dataset.py --section ecr  --month 2026-XX --input path/to/ECR.xlsx
python build_dataset.py --section posb --month 2026-XX --input path/to/POSB.xlsx
python build_dataset.py --section pli  --month 2026-XX --input path/to/PLI.xlsx
python build_dataset.py --section rpli --month 2026-XX --input path/to/RPLI.xlsx
# ...and the booking sections

python assemble.py
python -m http.server
```

Open `http://localhost:8000` and confirm the dashboard renders real WB
numbers. **Do not proceed to Part 4 until this works** — everything after
this point is wiring an already-working pipeline up to hosted
infrastructure.

---

## Part 4 — Google Drive + service account

This creates a "robot" Google identity (a **service account**) that can
read exactly one folder in your Drive and nothing else — not your email,
not your other files. Roughly 15 minutes.

### 4.1 — Create a Google Cloud project

1. Go to [console.cloud.google.com](https://console.cloud.google.com) and
   sign in with the Google account whose Drive will hold `DHCUploads`.
2. Top-left, click the project dropdown → **New Project**.
3. Name it something like `wb-division-health-report` → **Create**.
4. Wait for the creation notification, then confirm it is selected in the
   top-left dropdown.

### 4.2 — Enable the Google Drive API

1. In the top search bar, type **Drive API** and open **Google Drive API**.
2. Click **Enable**. (If it shows "Manage", it is already enabled — fine.)

### 4.3 — Create the service account

1. Hamburger menu ☰ → **IAM & Admin → Service Accounts**.
2. **+ Create Service Account**.
3. Name it `dhc-pipeline` → **Create and Continue**.
4. On "Grant this service account access", click **Continue** without
   adding any role. It needs no project-level permissions — only the one
   Drive folder shared in 4.5.
5. **Done**.
6. Click the new service account and note its **email address** — it looks
   like `dhc-pipeline@wb-division-health-report.iam.gserviceaccount.com`.
   You need this exact address in 4.5.

### 4.4 — Create and download the key

1. On that service account's page → **Keys** tab.
2. **Add Key → Create new key** → **JSON** → **Create**.
3. A `.json` file downloads. **Keep it private.** Anyone with this file
   can read the shared folder. Do not email it, do not commit it to
   GitHub.
4. You will paste its *contents* into a GitHub secret in Part 5.
   Afterwards store it somewhere secure (a password manager) in case you
   need to recreate the secret later.

### 4.5 — Create and share the DHCUploads folder

1. In Google Drive, create a folder named exactly **`DHCUploads`** at the
   top level of My Drive.
2. Right-click → **Share**.
3. Paste the service account email from 4.3.6 → role **Viewer** → **Send**
   (uncheck "Notify people" if offered — it is a robot account).

The pipeline can now list and download anything inside `DHCUploads`, and
nothing else in your Drive. The Apps Script creates dated subfolders
(`DHCUploads/2026-07/`) automatically as uploads arrive — you do not
create those by hand.

### 4.6 — Test it locally (recommended)

With the JSON key saved locally and **not** committed to git:

```powershell
# PowerShell
$env:GDRIVE_SA_KEY_FILE = "C:\path\to\dhc-key.json"
python drive_pull.py --month 2026-07 --dest downloads/
```

With nothing uploaded yet, every section should print `not uploaded yet
for 2026-07`. That confirms the credentials work and the folder is shared
correctly, without needing a real upload. Then upload a test file by hand
to `DHCUploads/2026-07/ECR.xlsx` and re-run to confirm a real download:

```bash
python drive_pull.py --month 2026-07 --section ecr --dest downloads/
```

**Drive troubleshooting:**

- *"Folder 'DHCUploads' not found"* — the name must match exactly
  (case-sensitive), and it must be shared with the **service account's**
  email, not your own.
- *403 / permission errors* — re-check 4.5; the service account needs at
  least Viewer.
- *Works locally but not in GitHub Actions* — the `GDRIVE_SA_KEY` secret
  must contain the **entire** JSON content, not a file path or a truncated
  paste.

---

## Part 5 — GitHub secrets and variables

On the **new West Bengal repo**: **Settings → Secrets and variables →
Actions**.

### 5.1 — Secrets

| Secret | Value | When |
|---|---|---|
| `GDRIVE_SA_KEY` | Entire JSON content from 4.4 | Now |
| `GMAIL_ADDRESS` | The Gmail address that sends uploader error emails | Now |
| `GMAIL_APP_PASSWORD` | 16-character App Password (see 5.2) | Now |
| `CLOUDFLARE_API_TOKEN` | From Part 8.3 | Part 8 |
| `CLOUDFLARE_ACCOUNT_ID` | From Part 8.3 | Part 8 |

### 5.2 — Creating a Gmail App Password

Regular Gmail passwords do not work for SMTP from a script. Google
requires an **App Password**, which only works if 2-Step Verification is
already on.

1. [myaccount.google.com/security](https://myaccount.google.com/security).
2. Under "How you sign in to Google", turn on **2-Step Verification** if
   it is not already on (you will need your phone).
3. Go to
   [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords).
4. Under "App name", type `dhc-pipeline` → **Create**.
5. Copy the 16-character password shown (spaces do not matter). This goes
   in `GMAIL_APP_PASSWORD`, **not** your regular Gmail password.

Without these two secrets, validation failures still correctly block
deployment — the uploader simply is not notified by email. Worth closing
out anyway. (AP never finished this step; it remains their one open item.)

### 5.3 — The AUTO_PROMOTE variable

**Variables** tab → **New repository variable**:

- Name: `AUTO_PROMOTE`
- Value: `false` (or simply do not create it — absent means off)

Leave this off until you trust the validation gate. When off, every
successful build deploys to **staging** only and you promote to production
yourself. Flip it to `true` later to deploy straight to production
automatically — this is the single flag to go fully automatic, no code
changes needed.

### 5.4 — Test before Cloudflare exists

Repo → **Actions** tab → **Data Pipeline** → **Run workflow** →
optionally a month (`YYYY-MM`) → **Run workflow**.

Expected right now: it pulls from Drive (probably finding nothing — fine,
it says so per section) and either does nothing, or builds, commits, and
then **fails at "Deploy to staging"** with a Cloudflare secret error. That
failure is expected until Part 8. Everything *before* it succeeding is
what you are checking.

### 5.5 — The three workflows, explained

**`pipeline.yml` — Data Pipeline.** Three triggers, all first-class:

1. `repository_dispatch` (type `data-upload`) — fires on each upload via
   Apps Script. Builds just the section that was uploaded.
2. `workflow_dispatch` — manual "update now", optional `month` input
   (defaults to current month). Rebuilds every section with a file on
   Drive for that month.
3. `schedule` — daily safety net at 06:30 UTC / 12:00 IST, in case a
   dispatch event is ever missed. Rebuilds the current month.

Steps: checkout → Python 3.12 → install deps → determine target month →
pull from Drive → **build and validate** → commit `data/` → stage public
files (`index.html` plus the seven JSON files only) → deploy to staging →
optionally auto-promote → on failure, email the uploader.

**`promote-production.yml` — Promote to Production.** Manual
(`workflow_dispatch`) only. This does **not** rebuild or re-validate
anything — it deploys exactly what is already committed on `main`, i.e.
what Data Pipeline last validated and pushed to staging. Review staging
first.

**`secret-scan.yml` — Secret Scan.** Runs gitleaks on `push` and
`pull_request`. It is deliberately a **separate workflow** — see Part 11,
issue 4 for why this matters.

---

## Part 6 — The intake Google Form

Google Forms has no import-from-spec option, so this is built by hand.
Follow it exactly: the Apps Script looks up answers **by exact question
title**, so a typo or a reworded question breaks the pipeline silently —
submissions get rejected as "missing field", logged but not processed.

### 6.1 — Create the Form

1. [forms.google.com](https://forms.google.com), signed in as the **same**
   Google account that owns `DHCUploads`.
2. **+ Blank form**.
3. Title: **Division Health Card — Monthly Data Upload**

### 6.2 — Description

```
Upload your section's monthly report here. Pick your Section and the
Reporting Month, then attach the file.

Download the blank template for your section first if you haven't
already — the file must match its column headers and sheet names exactly,
or it will be rejected automatically:
  [ link to your templates folder — see note below ]

One submission per section per month. If you need to correct a mistake,
just submit again with the corrected file — the newest submission for
that section+month replaces the previous one.

Exception: BO Lookup — Silent Accounts is a snapshot file, not a
correctable monthly report — resubmitting the same or an older
Reporting Month for it is rejected outright (not silently replaced),
since offices absent from a given month's file are meant to keep last
month's figures untouched. A genuine correction needs an admin to
re-process it manually from staging.

Questions? Contact [your name/email here].
```

**Template links:** the templates live in `/templates` in the repo, but if
the repo goes private your uploaders likely have no GitHub accounts. Copy
the files from `/templates` into a small read-only shared Drive folder
(e.g. `DHC Templates`, shared "Anyone with the link — Viewer") and link
that here instead. Re-copy them whenever `pipeline_config.yaml` changes
(run `generate_templates.py` first).

### 6.3 — Settings (gear icon, top right)

- **Responses** tab:
  - **Collect email addresses → Verified.** This is what lets Apps Script
    know who submitted, which the allowlist check and the error email both
    depend on.
  - **Limit to 1 response — leave OFF.** The same person needs to submit
    repeatedly (different sections, months, corrections). Turning it on
    would let each uploader submit exactly once, ever.

> **Do not skip the "Verified" setting.** AP missed this initially and
> *every* submission silently failed with "unauthorized email: (none
> collected)" until it was caught. Test it by opening the Form in a fresh
> incognito window — it must force a Google sign-in before showing any
> questions.

There is no native "restrict to specific people" option on a personal
Gmail account (that needs Google Workspace). Enforcement happens in Apps
Script instead, via `ALLOWED_EMAILS`.

### 6.4 — Question 1: Section

- Title (exact): `Section`
- Type: **Dropdown**, Required: **Yes**
- Options — exact text, must match `SECTION_LABEL_TO_KEY` in `Code.gs`:

```
ECR — Revenue & Expenditure
POSB — Accounts Opened/Closed
PLI — Policy Distribution
RPLI — Policy Distribution
Booking — Product-wise
Booking — Book-type-wise (daily)
BO Lookup — Silent Accounts
```

> Note the em-dashes (—), not hyphens. Copy-paste these rather than
> retyping them.

### 6.5 — Question 2: Reporting Month

- Title (exact): `Reporting Month`
- Type: **Dropdown**, Required: **Yes**
- Options — must match `MONTH_LABEL_TO_ISO` in `Code.gs`. This covers
  FY 2026-27; extend both places together when a new fiscal year starts:

```
April 2026
May 2026
June 2026
July 2026
August 2026
September 2026
October 2026
November 2026
December 2026
January 2027
February 2027
March 2027
```

### 6.6 — Question 3: Upload your file

- Title (exact): `Upload your file`
- Type: **File upload**, Required: **Yes**
- **Allow only specific file types** — leave **unrestricted**. Forms' file
  type checkboxes are broad categories with no plain "CSV" option;
  checking **Spreadsheet** covers `.xlsx` but would block the two Booking
  sections' `.csv` files. The pipeline's own validation already catches a
  wrong file type with a clear plain-language error back to the uploader.
- **Maximum number of files**: `1`
- **Maximum file size**: `25 MB`

Google sometimes asks you to re-confirm email collection after adding a
file-upload question — confirm it if prompted.

---

## Part 7 — Apps Script

Do this only after the Form is built exactly per Part 6.

### 7.1 — Open the script editor

1. Open your Form → **⋮** (top right) → **Script editor**. This creates a
   script *bound* to the Form, which is the only kind that gets full
   authorization — which matters in 7.4.
2. Delete the default `myFunction() {}` placeholder.
3. Paste in the entire contents of `apps_script/Code.gs` from the repo.
4. Edit these constants at the top for West Bengal:

| Constant | Set to |
|---|---|
| `ALLOWED_EMAILS` | The actual WB office-staff Google account addresses allowed to submit |
| `GITHUB_REPO` | Your new repo, as `owner/name` |
| `SECTION_LABEL_TO_KEY` | Must match `pipeline_config.yaml` section keys and labels exactly |
| `SECTION_CANONICAL_FILENAME` | Must match each section's `canonical_filename` in the YAML exactly — **see Appendix D, there is a known mismatch to fix** |
| `MONTH_LABEL_TO_ISO` | WB's fiscal year month list, matching the Form's dropdown |

5. **File → Save**. Name the project something like `DHC Form Handler`.

### 7.2 — Create the fine-grained GitHub PAT

This token needs exactly two permissions on exactly one repo — **not** a
classic token with broad `repo` scope.

1. GitHub → **your profile menu** → **Settings** → **Developer settings**
   → **Personal access tokens** → **Fine-grained tokens** → **Generate
   new token**.
2. **Token name**: `dhc-apps-script-dispatch`
3. **Expiration**: something you are comfortable renewing (e.g. 90 days);
   GitHub emails you before it expires.
4. **Repository access**: **Only select repositories** → your WB repo.
5. **Permissions → Repository permissions**:
   - **Contents: Read and write**
   - **Actions: Read and write** (this is what allows
     `repository_dispatch`)
   - Everything else: **No access**.
6. **Generate token** and copy it immediately — shown once.

> **Double-check both permissions explicitly.** Getting either wrong
> produces HTTP 403 "Resource not accessible by personal access token" on
> every dispatch attempt. AP hit exactly this during rollout — the token
> was created with `Actions` but not `Contents`, and every Form submission
> failed at the dispatch step. Editing the token's permissions in place
> fixes it without needing to update the Script Property again.

### 7.3 — Store the PAT in Script Properties (never in code)

1. In the Apps Script editor → gear icon **Project Settings**.
2. **Script Properties → Add script property**.
3. Property: `GITHUB_PAT`, Value: the token from 7.2.
4. **Save script properties**.

The script reads this via `PropertiesService` at run time — never visible
in code, never committed, readable only by this Apps Script project.

### 7.4 — Wire up the installable trigger

> **This is the step people miss.** A function named `onFormSubmit` does
> **not** run automatically just by existing. It must be explicitly bound
> as a trigger, and it must be an *installable* trigger — simple triggers
> are not allowed to call external services like `UrlFetchApp`.

1. Left sidebar → clock icon → **Triggers**.
2. **+ Add Trigger**.
3. Configure:
   - **Function to run**: `onFormSubmit`
   - **Deployment**: `Head`
   - **Event source**: `From form`
   - **Event type**: `On form submit`
4. **Save**. You will be asked to authorize the script (it needs Drive
   access and external request permission) — review and allow. This is
   your own script running as your own account; the prompt is expected.

### 7.5 — Test end to end

1. Submit a real test entry through the Form using one of the
   `ALLOWED_EMAILS` accounts, with a real section/month and a small file.
2. Apps Script editor → **Executions** — the most recent `onFormSubmit`
   should have succeeded.
3. Open the run's logs. You should see:
   - `Accepted: section=... month=... from=...`
   - `GitHub dispatch sent OK (HTTP 204)`
4. In Google Drive, confirm `DHCUploads/<month>/<canonical filename>` now
   exists.
5. On GitHub → **Actions** tab → a **Data Pipeline** run triggered by
   `repository_dispatch` should appear within seconds.

If step 3 shows "Rejected submission from unauthorized email", check that
the test email is in `ALLOWED_EMAILS` exactly (case-sensitive) and that
you saved the script after editing.

### 7.6 — What the script actually does

On each submission:

1. Rejects anything from an email not in `ALLOWED_EMAILS` (logged, not
   processed).
2. Copies the uploaded file to `DHCUploads/<YYYY-MM>/<canonical name>`,
   overwriting any previous file for that section+month. The original
   stays in the Form's own attachments folder as an audit trail.
3. Fires a GitHub `repository_dispatch` (type `data-upload`) so the
   pipeline picks it up within seconds.

No reminder emails, no other side effects — deliberately minimal.

### 7.7 — Keeping three places in sync, forever

`SECTION_LABEL_TO_KEY`, `SECTION_CANONICAL_FILENAME`, and
`MONTH_LABEL_TO_ISO` are **hand-maintained copies** of facts that also
live in `pipeline_config.yaml` and in the Form's dropdowns. There is no
automatic sync. If you add a section, rename one, or roll into a new
fiscal year, update **all three**:

1. `pipeline_config.yaml`
2. The Form's dropdown options
3. `apps_script/Code.gs`

This is the single most likely source of future silent breakage.
Appendix D documents a live example of what happens when they drift.

---

## Part 8 — Domain and Cloudflare hosting

Every step here is in an external console — Cloudflare, your registrar,
GitHub settings. Substitute West Bengal's domain everywhere.

**Why the order matters:** a brand-new domain has no live traffic, so
there is no downtime risk — but the dashboard holds real internal data, so
the order below puts the login gate in place **before** the custom domain
ever goes live. Do not reorder 8.6 and 8.7.

### 8.1 — Point the domain at Cloudflare

1. Sign in at [dash.cloudflare.com](https://dash.cloudflare.com). Use
   **one account** for everything — Pages, Access, and DNS all need to be
   together.
2. **Add a domain** → your WB domain → **Free** plan.
3. Cloudflare scans existing DNS and shows **two nameservers**, e.g.
   `ana.ns.cloudflare.com` / `bob.ns.cloudflare.com` (yours will differ —
   copy the exact ones shown).
4. At your registrar: **DNS → Nameservers → Change → Enter my own
   nameservers** → paste the two from step 3, delete the defaults →
   **Save**.
5. Back in Cloudflare, **Done, check nameservers**. This takes anywhere
   from minutes to 24 hours; Cloudflare emails you when active.

Wait for the domain to be active before continuing.

### 8.2 — Create the two Pages projects

From the repo root, with Node installed:

```bash
npx wrangler login
```

This opens a browser tab — click **Allow**. One-time only.

```bash
npx wrangler pages project create dhc-staging    --production-branch=staging
npx wrangler pages project create dhc-production --production-branch=main
```

You now have two empty Pages projects, each with a `*.pages.dev` URL. Note
both down. (You can name them `wb-staging` / `wb-production` if you
prefer — just change the `--project-name` flags in both workflow files to
match.)

### 8.3 — Get your API token and Account ID

**Account ID:** Cloudflare dashboard → **Workers & Pages** → the Account
ID is shown on the right.

**API token** (scoped narrowly — not your Global API Key):

1. Profile icon → **My Profile** → **API Tokens**.
2. **Create Token** → **Edit Cloudflare Workers** template → **Use
   template** (this covers Pages too).
3. Under **Account Resources**, scope it to your one account, not "All
   accounts".
4. **Continue to summary** → **Create Token**. Copy immediately.

### 8.4 — Add both as GitHub secrets

Repo → **Settings → Secrets and variables → Actions → New repository
secret**:

- `CLOUDFLARE_API_TOKEN`
- `CLOUDFLARE_ACCOUNT_ID`

Both workflows pick these up automatically.

### 8.5 — First real deploy

Repo → **Actions** → **Data Pipeline** → **Run workflow**. Watch "Deploy
to staging" — it should now succeed. Visit
`https://dhc-staging.pages.dev` and confirm the dashboard renders. **Do
not promote to production yet** — do 8.6 first.

### 8.6 — Lock down both pages.dev URLs before anything is public

1. Cloudflare → **Zero Trust**. First time, it asks for a **team name**
   (any name — it becomes part of your login page URL).
2. **Access → Applications → Add an application → Self-hosted**.
3. **Application name**: `DHC Production`; **Session duration**: e.g. 24
   hours; **Application domain**: `dhc-production.pages.dev`.
4. **Next** → add a policy:
   - **Policy name**: `Allowed viewers`
   - **Action**: `Allow`
   - **Include → Emails** → every address that should be able to view.
     This uses **One-Time PIN** by default — no identity provider needed;
     a visitor enters their email, gets a 6-digit code, and that is the
     login.
5. **Add application**.
6. Repeat for `dhc-staging.pages.dev` (name it `DHC Staging`) — same list,
   or a smaller one if you do not want staff previewing unapproved data.

Confirm in an incognito window: `https://dhc-production.pages.dev` should
show a Cloudflare login page, not the dashboard.

### 8.7 — Attach the custom domain

Only after 8.6 is confirmed working.

1. **Workers & Pages → dhc-production → Custom domains → Set up a custom
   domain**.
2. Enter your WB domain → **Continue** → **Activate domain**. Since DNS is
   already on Cloudflare, the required record is created automatically.
3. **Add a third Access application** for the custom domain itself (same
   process as 8.6). A custom domain is a **different hostname** from
   `dhc-production.pages.dev`, so it needs its own Access application even
   though it serves the same project.
4. Wait a minute or two for the certificate, then visit your domain.

### 8.8 — Decide your access model

Decide up front whether West Bengal's dashboard should be:

| Model | Fits when | How |
|---|---|---|
| **Public, no login** | Data is not sensitive, or the audience is too large to maintain a list | Simply do not create an Access application for the custom domain |
| **Explicit email list** | A short, fixed set of viewers | Access app → **Include → Emails** → list every address |
| **Email-domain match** ⭐ | "Every employee, nobody outside" | Access app → **Include → Emails ending in** → `@indiapost.gov.in` (use the real domain) |

**Recommended: email-domain match.** Anyone with an organizational email
self-serves a login via one-time PIN, with zero per-person admin work;
anyone without one cannot get in even with the URL.

> **What AP chose, and why:** AP originally completed the full Access
> setup, then **deliberately deleted** the custom domain's Access
> application to make `ehealthcard.in` fully public — 10,600+ offices made
> an individual allowlist impractical, and at the time the domain-match
> option was not adopted. Their two `.pages.dev` URLs remain gated. If
> West Bengal is at similar scale, go with the domain-match option rather
> than repeating the all-or-nothing choice.

Confirm afterward in an incognito window that the behaviour matches what
you intended.

### 8.9 — Flip the repo to private (optional)

1. Repo → **Settings → General → Danger Zone → Change visibility → Make
   private**.
2. Note: GitHub Actions minutes are unlimited on public repos but capped
   on a monthly quota for private repos on the Free plan. This pipeline
   runs a handful of times a day at most, so the quota is ample.

> **While the repo is public, `data/latest.json` and the roster files are
> readable by anyone directly through GitHub**, completely independent of
> whatever Cloudflare Access is or is not doing. If the data is sensitive,
> Access on the domain alone is *not* sufficient — the repo must be
> private too. AP has deferred this; decide deliberately for WB.

---

## Part 9 — Go-live checklist

- [ ] Local build (3.7) renders correctly with real WB data
- [ ] `known_divisions` verified character-for-character against a real WB
      ECR export
- [ ] `office_hierarchy.json` regenerated for WB
- [ ] Templates regenerated and circulated to uploaders
- [ ] `DHCUploads` created and shared with the service account (Viewer)
- [ ] `GDRIVE_SA_KEY` secret set and confirmed working
- [ ] `GMAIL_ADDRESS` / `GMAIL_APP_PASSWORD` secrets set
- [ ] Form built; **Collect email = Verified** confirmed by testing
      signed-out
- [ ] `Code.gs` constants updated for WB; **Appendix D mismatch fixed**
- [ ] Fine-grained PAT created with **both** Contents and Actions = Read
      and write
- [ ] PAT stored as Script Property `GITHUB_PAT`
- [ ] Installable trigger wired and confirmed firing
- [ ] One real end-to-end submission confirmed: Form → Drive → dispatch →
      build → staging
- [ ] Domain live on Cloudflare; both Pages projects deployed
- [ ] Access model decided and implemented (8.8)
- [ ] Repo visibility decided (8.9)
- [ ] `Promote to Production` tested at least once manually
- [ ] URL communicated to everyone who needs it

---

## Part 10 — Ongoing operations

**Day to day.** Branches submit through the Form. The pipeline validates,
builds, and deploys to staging automatically within seconds. The daily
cron run (06:30 UTC / 12:00 IST) is a safety net in case a dispatch event
is ever missed.

**Promoting to production.** GitHub → **Actions** → **Promote to
Production** → **Run workflow**. Manual by design, because GitHub's Free
plan has no approval gate for private repos. Review staging and the Data
Pipeline run's job summary first. Set `AUTO_PROMOTE` to `true` later to
skip this.

**A validation failure never reaches the live site.** Invalid uploads are
rejected with a plain-language reason emailed to the uploader (if the
`GMAIL_*` secrets are set), and the last good data stays live.

**Changing what a section validates or expects.** Edit
`pipeline_config.yaml` only — templates and validation both read from it,
so they cannot drift apart. Re-run `generate_templates.py` afterward and
recirculate the updated template.

**Adding a new section or a new fiscal year.** Update all three places
listed in 7.7.

**Correcting a bad upload.** For every section except BO Lookup, just
resubmit through the Form — the newest submission for that section+month
replaces the previous one. BO Lookup is a snapshot merge and rejects
resubmission of the same or an older month outright; a genuine correction
needs manual re-processing.

> **If you manually place a replacement file in Drive** instead of going
> through the Form (e.g. for testing): **delete the old file first.** Do
> not rely on drag-and-drop "replace" — Drive sometimes creates a renamed
> duplicate (`ECR (1).xlsx`) instead of overwriting, and the pipeline
> reads by exact filename, so a stray duplicate silently means your edit
> is never picked up.

---

## Part 11 — Troubleshooting

Every one of these is a real issue hit during AP's rollout. Each looked
like a different kind of failure at first.

**1. A GitHub Action run is green, but nothing changed on the dashboard.**
Green only means "no validation errors" — it is *also* green when there
was simply nothing new to build (wrong month on a manual run, or the file
never reached `DHCUploads`). Check the run's Job Summary for
"Rebuilt: ..." vs "nothing to build", and look for a new "Update dashboard
data" commit before assuming the data changed.

**2. Dispatch fails with HTTP 403 "Resource not accessible."** The PAT is
missing `Contents: Read and write`, or is not scoped to the right repo.
See 7.2. Editing the token's permissions in place usually works without
updating the `GITHUB_PAT` Script Property again.

**3. Apps Script log shows "unauthorized email: (none collected)."** The
Form's **Collect email addresses** is not set to **Verified**. See 6.3.

**4. Automatic (dispatch-triggered) runs fail, but manual runs succeed.**
`gitleaks-action` cannot run on `repository_dispatch` events at all — it
errors immediately with "The [repository_dispatch] event is not yet
supported." If secret scanning is embedded inside `pipeline.yml` in
whatever copy you are working from, **every Form-triggered run fails
before it even reaches your data**, while manual `workflow_dispatch` runs
look fine — which is exactly what made this hard to diagnose. In this
codebase it already lives in its own `secret-scan.yml` triggered on
`push`. Confirm that is true in your copy before relying on automatic
runs.

**5. A file "uploaded properly" to Drive, but the pipeline never finds
it.** Check whether it is sitting in the Form's own auto-generated
attachment folder (`<Form name> (File responses)/...`) instead of
`DHCUploads/<month>/<canonical name>`. That means Apps Script never
successfully processed the submission — see issues 2 and 3 for why. Also
check Appendix D, which is a second, distinct cause of exactly this
symptom.

**6. The domain loads without asking for login, but you expected it to be
gated.** Cloudflare Access applications are scoped **per hostname**.
Attaching a custom domain to a Pages project does **not** inherit the
Access policy already on the project's `*.pages.dev` URL. Each hostname
needs its own Access application. See 8.7 step 3.

**7. A Pages URL times out even though Access authentication succeeded**
(you got the PIN and it was accepted). The project likely has zero
deployments. `Promote to Production` does not build anything — it only
deploys what the pipeline already committed. If production was never
deployed to even once, there is nothing behind Access to serve. Check the
project's Deployments tab.

**8. A division's numbers are missing or the circle total is wrong.**
Almost certainly a `known_divisions` mismatch — a name in the config that
does not match the ECR export character-for-character is silently dropped.
See 3.3.

---

## Appendix A — Repository map

```
├── pipeline_config.yaml        ← single source of truth; start here
├── requirements.txt
├── index.html                  ← the entire dashboard, one self-contained file
│
├── pipeline/
│   ├── config.py               loads and validates pipeline_config.yaml
│   ├── common.py               roster loading, office geo, shared helpers
│   ├── validate.py             the CI validation gate
│   ├── flag_rules.py           derives data-quality flags
│   ├── drive.py                Google Drive read layer
│   ├── sections/               one module per section — extraction logic
│   │   ├── ecr.py
│   │   ├── posb.py
│   │   ├── pli.py  rpli.py  _pli_rpli_common.py
│   │   ├── posb_silent.py      snapshot-merge logic (different from the rest)
│   │   └── booking.py          also holds load_hierarchy()
│   └── derive/                 cross-section derived views
│       ├── office_status.py    OFFICE_STATUS_BY_MONTH
│       ├── subdiv_booking.py   SUBDIV_BOOKING
│       ├── subdiv_bolookup.py  sub-division BO rollup
│       ├── pli_rpli_cum.py     cumulative PLI/RPLI
│       └── trends.py           month-over-month trends
│
├── build_dataset.py            build ONE section for ONE month
├── assemble.py                 combine all months into data/latest.json
├── ci_build_sections.py        what the GitHub Action actually runs
├── drive_pull.py               download canonical files from Drive
├── generate_templates.py       regenerate /templates from the YAML
├── extract_premium_target.py   PLI/RPLI premium targets
├── migrate_ecr_targets.py      one-off ECR target migration
├── render_error_email.py       plain-language uploader error email
├── test_drive.py               Drive connectivity check
│
├── templates/                  blank files handed to uploaders (generated)
├── data/                       committed build output (deployed)
├── uploads/                    raw source files (never deployed)
├── apps_script/Code.gs         the Form handler
├── office_hierarchy.json       flattened office map for booking derivations
├── pli_id_overrides.json       per-office pli_id corrections (see 3.2)
└── .github/workflows/
    ├── pipeline.yml            Data Pipeline
    ├── promote-production.yml  manual production gate
    └── secret-scan.yml         gitleaks, on push only (see Part 11 #4)
```

### Script cheat sheet

| Command | Does |
|---|---|
| `python build_dataset.py --section X --month YYYY-MM --input FILE` | Builds one section for one month into `data/dataset_<month>.json` |
| `python assemble.py` | Combines every `data/dataset_*.json` into `data/latest.json` |
| `python ci_build_sections.py --month YYYY-MM --downloads downloads/` | What CI runs — detects which files are present, validates, builds, assembles |
| `python drive_pull.py --month YYYY-MM --dest downloads/` | Downloads all canonical files for a month |
| `python generate_templates.py` | Regenerates `/templates/*` from the YAML |
| `python -m http.server` | Serve the dashboard locally on :8000 |

---

## Appendix B — The seven sections

| Key | Form label | Canonical filename | Type | Cumulative mode |
|---|---|---|---|---|
| `ecr` | ECR — Revenue & Expenditure | `ECR.xlsx` | xlsx | `source` |
| `posb` | POSB — Accounts Opened/Closed | `POSB.xlsx` | xlsx | `computed` |
| `pli` | PLI — Policy Distribution | `PLI.xlsx` | xlsx | `computed` |
| `rpli` | RPLI — Policy Distribution | `RPLI.xlsx` | xlsx | `computed` |
| `posb_silent` | BO Lookup — Silent Accounts | `BO_Lookup_Upload.xlsx` | xlsx | `snapshot_merge` |
| `booking_productwise` | Booking — Product-wise | `Booking_Productwise.csv` | csv | `computed` |
| `booking_booktypewise` | Booking — Book-type-wise (daily) | `Booking_BookTypewise_Datewise.csv` | csv | `computed` |

### What `cumulative_mode` means

- **`source`** — the uploaded file already reports cumulative-to-date
  figures; the source system computes the running total. The pipeline does
  **not** sum this section across months; each month's file simply
  replaces the previous cumulative value. (ECR works this way.)
- **`computed`** — the file reports one month's activity; the pipeline
  accumulates across months itself.
- **`snapshot_merge`** — every upload is a full stock snapshot of the
  whole office universe at one point in time. Offices missing from a given
  month's upload **keep their last known snapshot** rather than going to
  zero. This is why re-uploading an older month is rejected outright
  rather than silently replacing.

### `row_count_band`

Each section declares a plausible range for its row count relative to the
expected office universe, e.g. `[0.7, 1.4]` for ECR or `[0.9, 1.1]` for
the BO Lookup snapshot (which should always cover nearly every office). A
file outside its band fails validation. Tune these for WB only if
legitimate files are being rejected.

### A note on ECR's shifting columns

ECR's header row includes columns whose position changes as the national
MIS adds fields — AP saw `PLI Online Apportionment` added in June 2026 and
`RPLI Revenue collected` in August 2026, each shifting every subsequent
column right by one. The config handles this with explicit `column:`
indices plus `match: prefix` for headers whose text legitimately changes
every month (e.g. `Total rev on sbcc up to <month>`). If a WB ECR file
suddenly fails header validation after a national MIS update, this is
where to look.

---

## Appendix C — Data model

`assemble.py` produces `data/latest.json` with these top-level keys, which
map directly onto the JavaScript global names the dashboard's loader
assigns them to:

| Key | Contents |
|---|---|
| `generated_from_months` | Which months contributed to this build |
| `POSB_BY_MONTH` | POSB accounts opened/closed per month |
| `PLI_POLICIES` / `RPLI_POLICIES` | Policy distribution |
| `BOOKING_BY_MONTH` | Booking activity |
| `ECR_BY_MONTH` | Per-division revenue/expenditure |
| `CIRCLE_FULL` | Circle-wide consolidated position (divisions + extra rows) |
| `SUBDIV_DATA` | Sub-division rollups |
| `OFFICE_STATUS_BY_MONTH` | Per-office reporting status |
| `SUBDIV_BOOKING` | Sub-division booking derivation |

**Deployed files.** Only these are copied into `dist/` and published:

```
index.html
data/latest.json
data/bo_lookup_latest.json
data/trends.json
data/flags.json
data/premium_target.json
data/bo_lookup_month_*.json
```

Everything else in the repo — pipeline source, `uploads/`,
`pipeline_config.yaml` — stays unpublished.

---

## Appendix D — Known issue to fix before go-live

**There is a live filename mismatch in the AP codebase you are copying.**
Fix it in the West Bengal copy before your first real book-type-wise
upload.

`pipeline_config.yaml` declares:

```yaml
booking_booktypewise:
  canonical_filename: "Booking_BookTypewise_Datewise.csv"
```

but `apps_script/Code.gs` writes:

```javascript
booking_booktypewise: 'Booking_BookTypewise.csv',
```

**Consequence.** The Apps Script saves a Form-submitted book-type-wise
file to Drive under a name the pipeline never looks for.
`pipeline/drive.py` resolves files strictly by the config's
`canonical_filename`, so the upload lands in `DHCUploads/<month>/`
successfully, the dispatch fires, the workflow runs, and the run goes
**green** — while that section is silently never built. This presents
exactly as Part 11's issue 1 and issue 5, which is what makes it hard to
spot.

**Fix.** Make the two strings identical. Either is fine as long as they
match; changing `Code.gs` to `Booking_BookTypewise_Datewise.csv` is the
smaller change, since the config value is also what `build_dataset.py`'s
documented usage refers to.

**Also worth doing:** after wiring everything up, verify **all seven**
canonical filenames match between `pipeline_config.yaml` and
`SECTION_CANONICAL_FILENAME` in `Code.gs`. The other six matched in AP's
copy as of this handover, but 7.7 explains why this class of drift
recurs.

---

## Getting help

If something fails, the most useful thing to capture is: **which step you
were on**, and **the exact error text or screenshot**. That is almost
always enough to tell whether it is a config typo or something in the code
that needs changing.

*Prepared from the AP Circle production system, September 2026.*
