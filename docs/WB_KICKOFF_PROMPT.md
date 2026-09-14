# West Bengal kickoff prompt

The first message to give Claude Code (or any coding agent) when starting the
West Bengal Circle build in VS Code.

**Before you paste it:** make sure `WEST_BENGAL_SETUP_GUIDE.md` is at the root of
the West Bengal repo. The prompt is useless without it — everything the agent
needs to know lives in that guide, and this prompt only tells it how to work
through it.

---

## The prompt

```
Read WEST_BENGAL_SETUP_GUIDE.md in full before doing anything else. It is the
complete, self-contained build guide for this system, handed over from AP Circle
where it runs in production. Do not skim it — later parts depend on earlier ones.

GOAL
Stand up the Division Health Card system for West Bengal Circle. This repo is a
fresh copy of the AP codebase with AP's data removed. I am starting from nothing.

YOUR SCOPE vs MINE
Part 3 of the guide is the only part that touches code — that is your main job.
Parts 4-8 are external consoles (Google Cloud, Drive, GitHub settings, Google
Forms, Apps Script, Cloudflare, my domain registrar). You cannot do those; walk
me through them one step at a time and wait for me to confirm each one before
moving on. Tell me explicitly whenever a step is mine.

GROUND RULES
1. pipeline_config.yaml is the single source of truth. Prefer changing it over
   changing code. Header/sheet/column changes need no code edits.
2. AP's values in the config are EXAMPLES, not defaults to keep. Anything
   circle-specific must come from real West Bengal files — never carry an AP
   value forward and never invent one. That applies especially to
   sections.ecr.known_divisions and circle_full_extra_rows: a name that does not
   match WB's real ECR export character-for-character is silently dropped from
   every total, with no error. Ask me for the file and read the names out of it.
3. If you need a source file I have not given you (the office roster, a real ECR
   export, geography files, a hierarchy export), stop and ask. Do not guess at
   WB's divisions, office counts, or column layouts.
4. Do not commit secrets. Service account keys, PATs and app passwords go in
   GitHub secrets or Apps Script Script Properties, never in the repo.

FIRST TASK — do this before any edits
Give me a short plan covering:
  a) Which files you need from me for Part 3, and what each must contain.
  b) What you can verify yourself right now vs what is blocked on me.
  c) Confirm whether Appendix D's filename mismatch is already fixed in this
     copy — check that all seven canonical filenames agree between
     pipeline_config.yaml and SECTION_CANONICAL_FILENAME in apps_script/Code.gs,
     and report the result.
Then stop and wait. Do not start editing until I have supplied the WB files.

DEFINITION OF DONE FOR PART 3
A local build of one real WB month renders correct numbers at localhost:8000,
per guide section 3.7. We do not touch Part 4 until that works.
```

---

## Have these ready before you start

The prompt will ask for them immediately, and Part 3 stalls without them:

| File | Why | Must contain |
|---|---|---|
| WB office roster | Every section reconciles against it | `office_id`, `office_name`, `office_type_code`, `division_name`, `sub_division_name`, `region_name` |
| One real WB ECR export | To read division names from | Whatever the national MIS produces — do not edit it first |
| Geography / lat-long files | Map and district views | Keyed by `office_id` |
| Hierarchy export (all office types) | Regenerating `office_hierarchy.json` | An `office_type_code` column covering every type, not just BPO/SPO/HPO |

The ECR export is the highest-risk item. `known_divisions` must match it exactly,
and a mismatch produces wrong totals with no error message — see guide section
3.3 and Part 11 issue 8.

## Why the prompt stops the agent twice

Once for a plan, once at the end of Part 3. With a guide this long the main
failure mode is an agent racing ahead and inventing West Bengal's division names
from AP's list. If you would rather it run more autonomously, delete the "Then
stop and wait" line and ground rule 3 — but then check `known_divisions` against
a real export yourself before trusting any number the dashboard shows.

## Note on Appendix D

Item (c) in the first task is a deliberate tripwire. The filename mismatch it
refers to was fixed in the AP repo in September 2026, so a fresh copy taken after
that will come back clean. A copy taken earlier still carries the bug, which
presents as a green pipeline run that silently never builds the book-type-wise
booking section. Either way you get an explicit answer instead of an assumption.
