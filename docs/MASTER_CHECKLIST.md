# Master checklist — everything left to do by hand

Everything in this repo (pipeline code, GitHub Action workflows, Apps
Script, all setup docs) has been built and tested as far as possible
without live access to Google/GitHub/Cloudflare consoles. This checklist
is only the steps that need *you*, across Phases 3–6, in the order that
avoids getting stuck. Full detail for each item is in the doc named next
to it — this is the scannable version.

**Nothing has been committed to git yet.** Everything so far is sitting
in your local working directory only. Say the word whenever you want it
committed — first commit is still an open step, not done automatically.

---

## Already reported done, by you

- [x] Phase 3 — GCP project, Drive API enabled, service account + key created (`docs/DRIVE_SETUP.md` steps 1–4)
- [x] Phase 4 — GitHub Action workflows built and reviewed
- [x] Phase 5 — Form + Apps Script setup completed

If any of these turn out to be only partially done, the relevant section
below still applies — just skip what you've already confirmed.

---

## Phase 3 — Google Drive (`docs/DRIVE_SETUP.md`)

- [ ] `DHCUploads` folder created at the top level of My Drive (exact name, case-sensitive)
- [ ] Folder shared with the **service account's email** (from the key file's `client_email`), role **Viewer**
- [ ] `GDRIVE_SA_KEY` secret added on GitHub (Settings → Secrets and variables → Actions) — full JSON key content
- [ ] *(Optional but recommended)* Tested locally: `python drive_pull.py --month <current> --dest downloads/` returns "not uploaded yet" for every section without erroring — confirms credentials + sharing are correct

## Phase 4 — Remaining GitHub Actions secrets (`docs/GITHUB_ACTIONS_SETUP.md`)

- [ ] 2-Step Verification turned on for `performancepulseapco@gmail.com` (required before an App Password can be created)
- [ ] Gmail **App Password** created at [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
- [ ] `GMAIL_ADDRESS` secret added = `performancepulseapco@gmail.com`
- [ ] `GMAIL_APP_PASSWORD` secret added = the 16-character app password
- [ ] *(Optional, leave off for now)* `AUTO_PROMOTE` repo variable — only set to `true` once you trust validation alone to go straight to production

## Phase 5 — Form + Apps Script (`docs/FORM_STRUCTURE.md`, `docs/APPS_SCRIPT_SETUP.md`)

- [ ] Form built with the exact 3 questions/titles/options specified
- [ ] Form settings: **Collect email (Verified)** on, **Limit to 1 response** OFF
- [ ] Templates copied somewhere your ~5 uploaders can actually reach (a shared read-only Drive folder is simplest, since the repo will be private) and linked in the Form description
- [ ] `apps_script/Code.gs` pasted into the Form's bound script editor
- [ ] `ALLOWED_EMAILS` in the script edited to the real ~5 office-staff addresses
- [ ] Fine-grained GitHub PAT created (Contents: read/write, Actions: read/write, scoped to this one repo only)
- [ ] PAT stored as Script Property `GITHUB_PAT` (never pasted into the code itself)
- [ ] Installable trigger created: function `onFormSubmit`, event source **From form**, event type **On form submit**
- [ ] End-to-end test: submitted a real test entry → Apps Script execution log shows "Accepted" + "GitHub dispatch sent OK" → file appears at `DHCUploads/<month>/<canonical name>` in Drive → a new run appears under the repo's Actions tab

## Phase 6 — Cloudflare cutover (`docs/CLOUDFLARE_CUTOVER.md`) — in progress

Do these **in order** — steps 6 and 7 specifically must not be swapped,
so the dashboard is never publicly reachable without a login, even
briefly.

1. [ ] GoDaddy nameservers changed to the two Cloudflare ones; Cloudflare confirms the domain is active
2. [ ] `dhc-staging` and `dhc-production` Pages projects created via `wrangler pages project create`
3. [ ] Cloudflare API token + Account ID obtained
4. [ ] `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID` secrets added on GitHub
5. [ ] Manual **Data Pipeline** run confirms "Deploy to staging" now succeeds; `dhc-staging.pages.dev` shows the real dashboard
6. [ ] Cloudflare Access (email OTP) applied to **both** `dhc-staging.pages.dev` and `dhc-production.pages.dev` — confirmed working (incognito hits a login page, not the dashboard)
7. [ ] Custom domain `ehealthcard.in` attached to the `dhc-production` project
8. [ ] Cloudflare Access application added for `ehealthcard.in` itself (separate from the `.pages.dev` one)
9. [ ] GitHub repo flipped to **private**
10. [ ] Old GitHub Pages site turned off (Settings → Pages → Source: None)
11. [ ] New URL (`https://ehealthcard.in`) sent to everyone who had the old `github.io` link bookmarked

## Final sanity pass, once everything above is checked off

- [ ] `https://ehealthcard.in` in an incognito window → Cloudflare login → email + PIN → dashboard loads with real data
- [ ] Submit one real Form entry end to end → confirm it lands on staging → run **Promote to Production** → confirm it's live on `ehealthcard.in`
- [ ] Decide when to ask me to make the first git commit — everything built this whole project is still local-only until you do

---

If anything on this list fails or behaves unexpectedly, tell me what step
and what you saw (error message, screenshot, whatever) — I can usually
tell from that whether it's a config typo or something in the code that
needs fixing.
