# Intake Google Form — exact structure to create manually

Google Forms has no "import from spec" option, so this has to be built by
hand in the Forms UI. Follow this exactly — the Apps Script in
`apps_script/Code.gs` looks up answers **by exact question title**, so a
typo or reworded question breaks the pipeline silently (submissions get
rejected as "missing field", logged but not processed).

## 1. Create the Form

1. Go to [forms.google.com](https://forms.google.com), sign in with the same Google account that owns `DHCUploads` (from `docs/DRIVE_SETUP.md`).
2. **+ Blank form**.
3. Title: **Division Health Card — Monthly Data Upload**

## 2. Description

Paste this into the description field under the title (edit the template
links once you've decided where templates live — see the note below):

```
Upload your section's monthly report here. Pick your Section and the
Reporting Month, then attach the file.

Download the blank template for your section first if you haven't
already — the file must match its column headers and sheet names exactly,
or it will be rejected automatically:
  [ link to templates — see note below ]

One submission per section per month. If you need to correct a mistake,
just submit again with the corrected file — the newest submission for
that section+month replaces the previous one.

Questions? Contact [your name/email here].
```

**Template links:** the templates live in `/templates` in the GitHub repo,
but the repo is private (from Phase 6 onward) and your ~5 uploaders likely
don't have GitHub accounts. Simplest fix: copy the 6 files from
`/templates` into a small **read-only shared Drive folder** (e.g.
`DHC Templates`, shared "Anyone with the link — Viewer") and link that
folder here instead of GitHub. Re-copy the files there whenever
`pipeline_config.yaml` changes (regenerate via `python generate_templates.py`
first).

## 3. Settings (gear icon, top right)

- **Responses** tab:
  - **Collect email addresses** → **Verified** (this is what lets
    Apps Script know who actually submitted, via
    `getRespondentEmail()` — required for the allowlist check and the
    error-notification email).
  - **Response receipts**: your choice, doesn't affect the pipeline.
  - **Limit to 1 response** — **leave this OFF.** The same person needs to
    submit repeatedly (different sections, different months, corrections).
    Turning this on would let each uploader submit exactly once, ever.
- There's no native "restrict to specific people" option on a personal
  Gmail account (that needs a Google Workspace domain) — enforcement
  happens in Apps Script instead, via the `ALLOWED_EMAILS` list. Requiring
  sign-in (which "Collect email addresses" does automatically) at least
  ensures every submission has a real, verified Google identity attached
  for that check to work against.

## 4. Questions — add in this order

### Question 1: Section

- Title (exact): `Section`
- Type: **Dropdown**
- Required: Yes
- Options (exact text, one per line — must match `apps_script/Code.gs`'s
  `SECTION_LABEL_TO_KEY` exactly):
  ```
  ECR — Revenue & Expenditure
  POSB — Accounts Opened/Closed
  PLI — Policy Distribution
  RPLI — Policy Distribution
  Booking — Product-wise
  Booking — Book-type-wise (daily)
  ```

### Question 2: Reporting Month

- Title (exact): `Reporting Month`
- Type: **Dropdown**
- Required: Yes
- Options (exact text — must match `apps_script/Code.gs`'s
  `MONTH_LABEL_TO_ISO`; this list covers FY 2026-27, extend both places
  together when a new fiscal year starts):
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

### Question 3: Upload your file

- Title (exact): `Upload your file`
- Type: **File upload**
- Required: Yes
- Settings:
  - **Allow only specific file types**: Google Forms' file-type checkboxes
    are broad categories (Documents, Spreadsheets, Presentations, etc.) and
    have no plain "CSV" option — checking **Spreadsheet** covers `.xlsx`
    uploads but would also block the two Booking sections' `.csv` files.
    Simplest: leave file types unrestricted here and let the pipeline's
    own validation catch the wrong kind of file — it already does (a
    `.csv` where an `.xlsx` was expected fails the sheet-name check
    immediately, with a clear plain-language error back to the uploader).
  - **Maximum number of files**: `1`
  - **Maximum file size**: `25 MB` (the largest current files run a few
    MB; this leaves headroom as the circle grows)

## 5. Turn on "Collect email" one more time if prompted

Google sometimes asks you to re-confirm email collection after adding the
file-upload question — confirm it if asked.

## 6. Next steps

Once the Form is built exactly as above, continue to
`docs/APPS_SCRIPT_SETUP.md` to wire up `apps_script/Code.gs`.
