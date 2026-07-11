# GitHub Actions setup — secrets & variables

The workflows in `.github/workflows/` need these secrets and one variable.
`GDRIVE_SA_KEY` should already be set from Phase 3 (`docs/DRIVE_SETUP.md`).
The Cloudflare ones (`CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`) can't
be created until Phase 6 sets up the Cloudflare Pages projects — until
then, the "Deploy to staging" step will fail cleanly (a clear "secret not
set" style error from `wrangler`), which is expected. Everything before
that step (pulling from Drive, validating, building, committing data) can
be tested now.

## Secrets needed (Settings → Secrets and variables → Actions → Secrets)

| Secret | From | Status |
|---|---|---|
| `GDRIVE_SA_KEY` | Phase 3, `docs/DRIVE_SETUP.md` step 6 | Should already be set |
| `GMAIL_ADDRESS` | Your Gmail address (`performancepulseapco@gmail.com`) | New — add now |
| `GMAIL_APP_PASSWORD` | See below | New — add now |
| `CLOUDFLARE_API_TOKEN` | Phase 6 | Not yet — add during Phase 6 |
| `CLOUDFLARE_ACCOUNT_ID` | Phase 6 | Not yet — add during Phase 6 |

## Creating a Gmail App Password (for uploader error emails)

Regular Gmail passwords don't work for SMTP from a script — Google
requires an **App Password**, which only works if 2-Step Verification is
already on for the account.

1. Go to [myaccount.google.com/security](https://myaccount.google.com/security).
2. Under "How you sign in to Google", make sure **2-Step Verification** is turned on (turn it on first if it isn't — you'll need your phone).
3. Once 2-Step Verification is on, go to [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords).
4. Under "App name", type something like `dhc-pipeline` → **Create**.
5. Google shows a 16-character password (spaces don't matter). Copy it — this is what goes in the `GMAIL_APP_PASSWORD` secret, **not** your regular Gmail password.

Then on GitHub: **Settings → Secrets and variables → Actions → New repository secret**
- `GMAIL_ADDRESS` = `performancepulseapco@gmail.com`
- `GMAIL_APP_PASSWORD` = the 16-character password from step 5

## The AUTO_PROMOTE variable (optional, off by default)

**Settings → Secrets and variables → Actions → Variables tab → New repository variable**
- Name: `AUTO_PROMOTE`
- Value: `false` (or just don't create it — absent means off)

Leave this off until you trust the validation gate alone. When off,
every successful build deploys to **staging** only, and you promote to
production yourself (see `.github/workflows/promote-production.yml`).
Flip it to `true` later to make Data Pipeline deploy straight to
production automatically — this is the "single config flag" to go fully
automatic, no code changes needed.

## Testing before Phase 6

Trigger a manual run to confirm everything up through "Commit updated
data" works, even though the Cloudflare step isn't set up yet:

**From the GitHub website:** Repo → **Actions** tab → **Data Pipeline** (left
sidebar) → **Run workflow** → optionally fill in a month (`YYYY-MM`) →
**Run workflow**.

**From the GitHub mobile app:** open the repo → **Actions** tab → **Data
Pipeline** → **Run workflow** → same as above.

Expected outcome right now: it pulls from Drive (probably finding nothing
uploaded yet — that's fine, it'll say so per section), and either does
nothing (if nothing was found) or builds+commits+then fails at "Deploy to
staging" with a Cloudflare secret error. That failure is expected until
Phase 6; everything before it succeeding is what to check for now.
