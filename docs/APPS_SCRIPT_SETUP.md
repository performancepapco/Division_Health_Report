# Apps Script setup

Do this after building the Form exactly per `docs/FORM_STRUCTURE.md`.

## 1. Open the script editor

1. Open your Form → click the **⋮** (three dots) top right → **Script editor**.
   (This creates a script *bound* to the Form — it can read its responses directly, and that's the only kind of trigger that gets full authorization, which matters in step 4.)
2. Delete the default empty `myFunction() {}` placeholder.
3. Copy the entire contents of `apps_script/Code.gs` from this repo and paste it in.
4. At the top of the pasted code, edit two things for your real setup:
   - `ALLOWED_EMAILS` — replace the placeholder emails with the actual ~5 office-staff Google account addresses that should be allowed to submit.
   - `GITHUB_REPO` — already set to `performancepapco/Division_Health_Report`; change only if the repo moves.
5. **File → Save** (or Ctrl/Cmd+S). Name the project something like `DHC Form Handler`.

## 2. Create the fine-grained GitHub PAT

This token needs exactly two permissions on exactly this one repo —
**not** a classic token with broad `repo` scope.

1. On GitHub: **Settings** (your profile menu, not the repo's) → **Developer settings** → **Personal access tokens** → **Fine-grained tokens** → **Generate new token**.
2. **Token name**: `dhc-apps-script-dispatch`
3. **Expiration**: pick something you're comfortable renewing periodically (e.g. 90 days) — GitHub will email you before it expires.
4. **Repository access**: **Only select repositories** → choose `performancepapco/Division_Health_Report`.
5. **Permissions** → **Repository permissions**:
   - **Contents**: **Read and write**
   - **Actions**: **Read and write** (this is what lets it fire `repository_dispatch`)
   - Leave everything else at **No access**.
6. **Generate token**. Copy it immediately — GitHub only shows it once.

## 3. Store the PAT in Script Properties (never in code)

1. Back in the Apps Script editor: gear icon (⚙️ **Project Settings**) in the left sidebar.
2. Scroll to **Script Properties** → **Add script property**.
3. Property: `GITHUB_PAT`
4. Value: paste the token from step 2.
5. **Save script properties**.

The script reads this via `PropertiesService` at run time — it's never
visible in the code, never committed anywhere, and only this Apps Script
project can read it.

## 4. Wire up the installable trigger

This is the step people usually miss — a function named `onFormSubmit`
does **not** run automatically just by existing. It needs to be
explicitly bound as a trigger, and it must be an *installable* trigger
(not a simple one) because simple triggers aren't allowed to call
external services like `UrlFetchApp`.

1. Left sidebar, clock icon → **Triggers**.
2. **+ Add Trigger** (bottom right).
3. Configure:
   - **Choose which function to run**: `onFormSubmit`
   - **Choose which deployment should run**: `Head`
   - **Select event source**: `From form`
   - **Select event type**: `On form submit`
4. **Save**. You'll be asked to authorize the script (it needs Drive access and external request permission) — review and allow it. This is your own script running as your own account, so this prompt is expected.

## 5. Test it end to end

1. Submit a real test entry through the Form yourself (using one of the `ALLOWED_EMAILS` accounts), picking a real section/month and a small test file.
2. In the Apps Script editor: clock icon → **Triggers**, or **Executions** (also left sidebar) — check the most recent execution for `onFormSubmit` succeeded (no red error).
3. Check **Executions** → click the run → view logs. You should see:
   - `Accepted: section=... month=... from=...`
   - `GitHub dispatch sent OK (HTTP 204)`
4. In Google Drive, confirm `DHCUploads/<month>/<canonical filename>` now exists with your test file's content.
5. On GitHub: **Actions** tab → the **Data Pipeline** workflow should show a new run, triggered by `repository_dispatch`, within a few seconds of your submission.

If step 3 shows a rejection log instead ("Rejected submission from
unauthorized email"), double check the email you tested with is in
`ALLOWED_EMAILS` exactly (case-sensitive) and that you saved the script
after editing it.

## 6. Keeping this in sync going forward

`apps_script/Code.gs`'s `SECTION_LABEL_TO_KEY`, `SECTION_CANONICAL_FILENAME`,
and `MONTH_LABEL_TO_ISO` maps are hand-maintained copies of facts that
also live in `pipeline_config.yaml` and the Form's own dropdown options —
there's no automatic sync between the three. If you ever add a section,
rename one, or roll into a new fiscal year, update all three places:
`pipeline_config.yaml`, the Form's dropdowns (`docs/FORM_STRUCTURE.md`),
and this script.
