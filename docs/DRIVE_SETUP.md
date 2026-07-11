# Google Drive integration — setup checklist

This is a one-time setup. It creates a "robot" Google identity (a
**service account**) that can only read one specific folder in your
Drive — it can't see your email, your other files, or anything else. The
automated pipeline uses it to download whatever divisions have uploaded
each month.

Do these steps in order. Total time: ~15 minutes.

---

## 1. Create a Google Cloud project

1. Go to [console.cloud.google.com](https://console.cloud.google.com) and sign in with the Google account you're using for this project (the one whose Drive will hold `DHCUploads`).
2. Top-left, click the project dropdown (next to "Google Cloud") → **New Project**.
3. Name it something like `division-health-report` → **Create**.
4. Wait for the notification that the project was created, then make sure it's selected in the top-left dropdown.

## 2. Enable the Google Drive API

1. In the search bar at the top, type **Drive API** and open **Google Drive API** from the results.
2. Click **Enable**. (If it's already enabled, you'll see "Manage" instead — that's fine, skip ahead.)

## 3. Create the service account

1. In the left sidebar (hamburger menu ☰) go to **IAM & Admin → Service Accounts**.
2. Click **+ Create Service Account** at the top.
3. Name it `dhc-pipeline` (or anything recognizable) → **Create and Continue**.
4. On the "Grant this service account access" step, click **Continue** without adding any role — it doesn't need project-level permissions, only the one Drive folder we'll share in step 5.
5. Click **Done**.
6. You'll land back on the Service Accounts list. Click the one you just created, note its **email address** — it looks like `dhc-pipeline@division-health-report.iam.gserviceaccount.com`. You'll need this exact address in step 5.

## 4. Create and download the key

1. Still on that service account's page, go to the **Keys** tab.
2. **Add Key → Create new key** → choose **JSON** → **Create**.
3. A `.json` file downloads automatically. **Keep it safe and private** — anyone with this file can read the shared folder. Don't email it, don't commit it to GitHub, don't put it in the repo.
4. You'll paste its *contents* into a GitHub secret in step 6, then you can delete the local copy (or keep it somewhere secure like a password manager, in case you need to regenerate the GitHub secret later).

## 5. Create and share the DHCUploads folder

1. In Google Drive (the same Google account), create a folder named exactly **`DHCUploads`** at the top level of My Drive.
2. Right-click it → **Share**.
3. Paste the service account's email from step 3.6 → set its role to **Viewer** → **Send** (uncheck "Notify people" if it's offered — it's a robot account, it won't read the email).
4. That's it — the pipeline can now list and download anything placed inside `DHCUploads`, and nothing else in your Drive.

The Apps Script (Phase 5) will create dated subfolders inside this automatically (`DHCUploads/2026-07/`, etc.) as branches upload files — you don't need to create those by hand.

## 6. Add the key as a GitHub secret

1. Open the downloaded JSON key file from step 4 in a text editor, select all, copy.
2. On GitHub, go to this repo → **Settings → Secrets and variables → Actions**.
3. **New repository secret**.
4. Name: `GDRIVE_SA_KEY`
5. Value: paste the entire JSON file content (starts with `{"type": "service_account", ...}`).
6. **Add secret**.

The GitHub Action (Phase 4) reads this automatically — nothing else to configure there.

## 7. Test it locally (optional, but recommended before Phase 4)

From the repo root, with the JSON key file saved locally (e.g. as `dhc-key.json`, **not committed to git** — it's already covered by `.gitignore`'s general `*.json` exclusions for anything outside `data/`/`templates/`, but double-check before committing anything):

```
# PowerShell
$env:GDRIVE_SA_KEY_FILE = "C:\path\to\dhc-key.json"
python drive_pull.py --month 2026-07 --dest downloads/
```

With nothing uploaded yet, every section should print `not uploaded yet for 2026-07` — that confirms the credentials work and the folder is shared correctly, without needing a real upload first. Upload a test file to `DHCUploads/2026-07/ECR.xlsx` by hand in Drive and re-run to confirm a real download works end to end:

```
python drive_pull.py --month 2026-07 --section ecr --dest downloads/
```

## Troubleshooting

- **"Folder 'DHCUploads' not found"** — the folder name must match exactly (case-sensitive), and it must be shared with the *service account's* email (from step 3.6), not your own.
- **403 / permission errors** — re-check step 5.3; the service account needs at least Viewer access.
- **Works locally but not in GitHub Actions** — confirm the `GDRIVE_SA_KEY` secret contains the *entire* JSON file content, not a path or a truncated paste.
