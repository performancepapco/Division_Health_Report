# Master checklist — everything left to do by hand

Everything in this repo (pipeline code, GitHub Action workflows, Apps
Script, all setup docs) has been built and tested as far as possible
without live access to Google/GitHub/Cloudflare consoles. This checklist
is only the steps that need *you*, across Phases 3–6, in the order that
avoids getting stuck. Full detail for each item is in the doc named next
to it — this is the scannable version.

**Everything has been committed and pushed to GitHub.** This checklist
now mostly reflects *history* — what was done and in what order — rather
than open steps. Remaining open items are marked accordingly below.

---

## Confirmed done, end to end

- [x] Phase 3 — Drive fully wired: service account, `DHCUploads`, `GDRIVE_SA_KEY` — real Form uploads land there correctly
- [x] Phase 4 — GitHub Action workflows built, tested, and fixed after two real bugs found in production use (a PAT missing `Contents: write` causing dispatch 403s, and `gitleaks-action` rejecting `repository_dispatch` — both resolved, see git history)
- [x] Phase 5 — Form + Apps Script fully working: a real submission goes Form → Apps Script → `DHCUploads` → GitHub dispatch → validated build → staging deploy, confirmed live
- [x] Phase 6 — Domain live, both Pages projects deployed, custom domain attached, promotion tested end to end. **Access was set up then deliberately removed from `ehealthcard.in`** — see below.

If any of these turn out to need revisiting, the relevant section below
still has the detail.

---

## Phase 3 — Google Drive (`docs/DRIVE_SETUP.md`) — done

- [x] `DHCUploads` folder created, shared with the service account (Viewer)
- [x] `GDRIVE_SA_KEY` secret added on GitHub
- [x] Confirmed working with real Form uploads, not just the empty-folder local test

## Phase 4 — Remaining GitHub Actions secrets (`docs/GITHUB_ACTIONS_SETUP.md`) — Gmail secrets unconfirmed

- [ ] 2-Step Verification turned on for `performancepulseapco@gmail.com`
- [ ] Gmail **App Password** created
- [ ] `GMAIL_ADDRESS` / `GMAIL_APP_PASSWORD` secrets added on GitHub
      — **not yet confirmed done.** Without these, the "email uploader on
      failure" step in `pipeline.yml` will itself fail quietly whenever it
      tries to run (a validation failure still blocks deployment correctly
      either way — this only affects whether the uploader gets notified by
      email about it). Worth closing out even though nothing's broken by
      its absence.
- [ ] *(Optional, leave off)* `AUTO_PROMOTE` repo variable

## Phase 5 — Form + Apps Script (`docs/FORM_STRUCTURE.md`, `docs/APPS_SCRIPT_SETUP.md`) — done, confirmed end to end

- [x] Form built, **Collect email (Verified)** correctly enabled (this was missed initially — submissions were rejected as unauthorized with no email collected until fixed)
- [x] `apps_script/Code.gs` deployed with real `ALLOWED_EMAILS`
- [x] Fine-grained GitHub PAT created and corrected to include `Contents: Read and write` (the initial token caused dispatch 403s until this was fixed)
- [x] PAT stored as Script Property `GITHUB_PAT`
- [x] Installable trigger wired up and confirmed firing
- [x] Full real end-to-end test passed: Form submission → Apps Script → `DHCUploads` → GitHub dispatch → validated build → staging deploy

## Phase 6 — Cloudflare cutover (`docs/CLOUDFLARE_CUTOVER.md`) — done, with one deliberate deviation

1. [x] GoDaddy nameservers changed to Cloudflare; domain active
2. [x] `dhc-staging` and `dhc-production` Pages projects created
3. [x] Cloudflare API token + Account ID obtained
4. [x] `CLOUDFLARE_API_TOKEN` / `CLOUDFLARE_ACCOUNT_ID` secrets added on GitHub
5. [x] Manual **Data Pipeline** run confirmed "Deploy to staging" works; `dhc-staging.pages.dev` shows the real dashboard
6. [x] Cloudflare Access applied to both `.pages.dev` URLs — **still in place today**
7. [x] Custom domain `ehealthcard.in` attached to `dhc-production`
8. [x] Access application added for `ehealthcard.in`, then **deliberately deleted** — the dashboard is intentionally public now, given 10,600+ offices made an individual allowlist impractical. See `docs/CLOUDFLARE_CUTOVER.md` §11 for restricting it again later (explicit list or, recommended at this scale, an email-domain match).
9. [ ] GitHub repo flipped to **private** — still deferred, your call. Reminder: while public, `data/latest.json` and the roster files are readable by anyone directly through GitHub, independent of whatever Cloudflare Access is or isn't doing.
10. [x] Old GitHub Pages site turned off
11. [ ] New URL (`https://ehealthcard.in`) — now public, so "recirculating" it is just normal communication, not access-granting

## Final sanity pass

- [x] `https://ehealthcard.in` loads the dashboard directly (no login, by design)
- [x] Real end-to-end test confirmed: Form submission → staging → **Promote to Production** → live on `ehealthcard.in`
- [x] First git commit made, and everything since has been pushed

---

If anything on this list fails or behaves unexpectedly, tell me what step
and what you saw (error message, screenshot, whatever) — I can usually
tell from that whether it's a config typo or something in the code that
needs fixing.
