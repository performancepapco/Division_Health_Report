# Cloudflare cutover checklist — ehealthcard.in

> **Current status:** `ehealthcard.in` is **public, no login** — a
> deliberate decision (10,600+ offices' worth of employees made an
> individual email allowlist impractical), made after originally
> completing this checklist with Access enabled. The `DHC Custom Domain`
> Access application from step 7.3 was later **deleted** to make this
> happen. See **§11** at the bottom for how to restrict it again —
> either back to an explicit list or (recommended at this scale) an
> email-domain match, so every employee self-serves without per-person
> admin work.

Every step here is in an external console (Cloudflare, GoDaddy, GitHub
settings) — none of it is something I can do for you, so this is written
as an exact, ordered checklist rather than code.

**Why this order matters:** `ehealthcard.in` is a brand-new domain with
no existing live traffic, so there's no "downtime" risk — but the
dashboard contains real internal data, so the order below sets up the
Cloudflare Access login gate **before** the custom domain ever goes live,
so the site is never reachable without authentication, not even briefly.
Don't reorder steps 6 and 7.

---

## 1. Point the domain at Cloudflare

1. Sign up / log in at [dash.cloudflare.com](https://dash.cloudflare.com) (use the same account for everything below — Pages, Access, DNS all need to be one account).
2. **Add a domain** → type `ehealthcard.in` → choose the **Free** plan.
3. Cloudflare scans for existing DNS records (likely just GoDaddy's default parking records) and shows you **two nameservers** — something like:
   ```
   ana.ns.cloudflare.com
   bob.ns.cloudflare.com
   ```
   (yours will be different — copy the exact ones shown to you).
4. In GoDaddy: **My Products → ehealthcard.in → DNS → Nameservers → Change** → **Enter my own nameservers (advanced)** → paste in the two from step 3 (delete GoDaddy's defaults) → **Save**.
5. Back in Cloudflare, click **Done, check nameservers**. This can take anywhere from a few minutes to 24 hours; Cloudflare emails you when it's active. You can also check anytime with **Check nameservers now** on that page.

Wait for Cloudflare to confirm the domain is active before continuing.

## 2. Create the two Pages projects (CLI, one-time)

Run these from the repo root, in a terminal with Node installed (already confirmed present on this machine):

```
npx wrangler login
```
This opens a browser tab — click **Allow** to authorize wrangler with your Cloudflare account. One-time only.

```
npx wrangler pages project create dhc-staging --production-branch=staging
npx wrangler pages project create dhc-production --production-branch=main
```

Each command will ask a couple of quick questions (production branch name — answer as shown above). When done, you'll have two empty Pages projects, each with its own `*.pages.dev` URL (e.g. `dhc-staging.pages.dev`, `dhc-production.pages.dev`) — note these down, you'll need them in step 4.

## 3. Get your Cloudflare API token and Account ID

**Account ID:**
1. Cloudflare dashboard → **Workers & Pages** (left sidebar).
2. Your **Account ID** is shown on the right side of that page — copy it.

**API token** (scoped narrowly — not your Global API Key):
1. Click your profile icon (top right) → **My Profile** → **API Tokens** tab.
2. **Create Token** → find **Edit Cloudflare Workers** template → **Use template** (this covers Pages too).
3. Under **Account Resources**, make sure it's scoped to your one account (not "All accounts").
4. **Continue to summary** → **Create Token**. Copy it immediately — shown once.

## 4. Add both as GitHub secrets

Repo → **Settings → Secrets and variables → Actions → New repository secret**:
- `CLOUDFLARE_API_TOKEN` = the token from step 3
- `CLOUDFLARE_ACCOUNT_ID` = the account ID from step 3

`pipeline.yml` and `promote-production.yml` (already built in Phase 4) pick these up automatically — nothing else to configure there.

## 5. Do a first real deploy

Trigger the pipeline manually to confirm the Cloudflare step works now: repo → **Actions** tab → **Data Pipeline** → **Run workflow**. Watch the "Deploy to staging" step — it should now succeed instead of failing on a missing secret. Visit `https://dhc-staging.pages.dev` to confirm the dashboard actually renders. Don't run **Promote to Production** yet — do step 6 first.

## 6. Lock down both pages.dev URLs with Cloudflare Access *before* anything is public

1. Cloudflare dashboard → **Zero Trust** (left sidebar). First time here, it'll ask you to pick a **team name** (any name, e.g. `aphealthcard` — this becomes part of your login page URL, doesn't need to be memorable).
2. **Access → Applications → Add an application → Self-hosted**.
3. **Application name**: `DHC Production`
   **Session duration**: your choice (e.g. 24 hours)
   **Application domain**: enter `dhc-production.pages.dev`
4. **Next** → add a policy:
   - **Policy name**: `Allowed viewers`
   - **Action**: `Allow`
   - **Include** → **Emails** → list every email address that should be able to view the dashboard (the ~5 office staff, yourself, anyone else). This uses **One-Time PIN** by default — no extra identity-provider setup needed; an allowed visitor enters their email, gets a 6-digit code by email, and that's their login.
5. **Add application**.
6. Repeat steps 2–5 for `dhc-staging.pages.dev` (application name `DHC Staging`) — same email list, or a smaller one if you don't want branch staff previewing unapproved data.

Confirm it worked: open `https://dhc-production.pages.dev` in an incognito window — you should hit a Cloudflare login page (email + PIN), not the dashboard directly.

## 7. Attach the custom domain — only after step 6 is confirmed working

1. **Workers & Pages** → **dhc-production** → **Custom domains** tab → **Set up a custom domain**.
2. Enter `ehealthcard.in` → **Continue** → **Activate domain**. Since DNS is already on Cloudflare (step 1), the required DNS record is created for you automatically — no manual DNS entry needed.
3. Add a second Access application for `ehealthcard.in` itself (repeat step 6's process once more, application name `DHC Custom Domain`, same email list) — a custom domain is a different hostname from `dhc-production.pages.dev`, so it needs its own Access application even though it points at the same Pages project.
4. Wait a minute or two for the certificate to provision, then visit `https://ehealthcard.in` — you should hit the same Access login page, then the dashboard after entering a valid email + PIN.

   **(Later reversed — see the status note at the top.)** `DHC Custom
   Domain` was deleted to make the site public. `dhc-production.pages.dev`
   and `dhc-staging.pages.dev` still have their own Access applications
   and remain login-gated; only the custom domain is open.

(Optional) If you also want `www.ehealthcard.in` to work, repeat step 7.1–7.2 for that hostname too.

## 8. Flip the GitHub repo to private

1. Repo → **Settings → General** → scroll to **Danger Zone** → **Change visibility** → **Make private** → follow the confirmation prompts.
2. Note for later: GitHub Actions minutes are unlimited on public repos but capped on a monthly quota for private repos on the Free plan. Given this pipeline runs a handful of times a day at most, that quota should be more than enough — just something to be aware of if Actions usage ever looks unexpectedly high.

## 9. Turn off the old GitHub Pages site and recirculate the new URL

1. Repo → **Settings → Pages** → under **Build and deployment**, set **Source** to **None** (or it may already be non-functional once the repo is private, since GitHub Pages for private repos needs a paid plan — either way, explicitly turning it off is cleaner).
2. The old `*.github.io` URL will 404 from this point on. **Send the new URL (`https://ehealthcard.in`) to everyone who had the old link bookmarked** — this won't happen automatically.

## 10. Ongoing: promoting to production

Day to day, the pipeline deploys to staging automatically. When you're happy with what's on `dhc-staging.pages.dev`, promote it: **Actions** tab → **Promote to Production** → **Run workflow**. See `docs/GITHUB_ACTIONS_SETUP.md` for the `AUTO_PROMOTE` flag if you later want to skip this manual step.

## 11. Restricting `ehealthcard.in` again, when you're ready

Two ways to do this, pick based on how you want to manage the list:

**A. Explicit email list** (fine for a small, fixed set of people):
1. Cloudflare dashboard → **Zero Trust → Access → Applications → Add an application → Self-hosted**.
2. **Application name**: `DHC Custom Domain`, **Application domain**: `ehealthcard.in`.
3. **Next** → policy **Allowed viewers**, **Action: Allow**, **Include → Emails** → list every allowed address → **Add application**.

**B. Email-domain match** (recommended at 10,600+ offices' scale — nobody needs to be added individually):
1. Same steps as A, but under **Include**, choose **Emails ending in** instead of **Emails**, and enter your organizational domain (e.g. `@indiapost.gov.in` — use the real one).
2. Anyone with an email on that domain can self-serve a login (email → one-time PIN) with zero admin work per person; anyone without it can't get in even with the URL.

Either way, confirm afterward in an incognito window: `https://ehealthcard.in` should show the Access login page again instead of loading directly.
