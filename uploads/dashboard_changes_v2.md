# AP Circle Dashboard — Consolidated Change Spec v2

**Context for Claude Code:** This document specifies all changes to be made in one implementation pass to the existing dashboard at `https://performancepapco.github.io/Division_Health_Report/`. Implement everything in this spec together to avoid iterative token cost. Follow the existing design language; this spec covers **content, logic, and structural changes only**.

---

## 1. NEW: Circle-level overview

### Add "AP Circle (Overview)" as first option in division dropdown

When selected, the layout reconfigures as follows:

**Header tile (replaces composite score with Pro-rata Achievement %):**
```
Headline: % Prop. Achievement for April 2026
Formula: Total April Revenue / Pro-rata of FY 2026-27 Directorate Target
Value:   107.18 / 76.64 = 139.85% (round to ceiling for display → 140%)
```
*Show both the percentage AND the underlying ratio (₹107.18 Cr / ₹76.64 Cr)*

**Region cards (3, ranked by % achievement):**
- Sort the three regions descending by % achievement vs proportionate target
- Each card shows: Rank badge (#1, #2, #3), Region name, FY 2026-27 Target, April Achievement, % of Prop. Target, and visual indicator (green/amber/red) for whether the region is on/below proportionate growth pace
- Use Region abbreviations consistently (see section 4)

**Other tabs (Verticals, Booking, etc.) when Circle selected:**
- Show circle-level rollups instead of division-level data
- ECR card stays as-is (already circle-level)
- Add a new sub-section under ECR: "Region-wise % Achievement vs Pro-rata Pace" — 3-row mini-table

---

## 2. Terminology — global replacements

| Find | Replace with |
|------|--------------|
| `FY27` | `FY 2026-27` |
| `pp` (percentage points) | `%` |
| `EBOs` (External Business Outlets) | `EBOs` — but redefine as **Excluding Branch Post Offices** |
| `OBOs` (Other Business Outlets) | `OBOs` — but redefine as **Only Branch Post Offices** |
| `Composite Score` (on Circle view) | `% Prop. Achievement` |
| `ARPU` (when shown inline) | Keep abbreviation, define in Notes tab |
| `Avg: 92.1` next to composite score | **REMOVE** (it was the circle composite average — not meaningful for users) |
| `VIS` | `VSP` (Visakhapatnam) |
| `Vij` | `VJA` (Vijayawada) |
| `KUR` | `KNL` (Kurnool) |

**Important content fix:** Earlier dashboard text described EBOs as "External Business Outlets / e-commerce-business mail" and OBOs as "Other Business Outlets / regular mail". This was wrong. Correct definitions:
- **EBO = Excluding Branch Post Offices** (delivery performance of mail delivered through HPOs, SPOs, etc. — non-BO offices)
- **OBO = Only Branch Post Offices** (delivery performance through Branch Post Offices only)

This explains why EBO delivery (~95%+) is consistently higher than OBO (~85-90%) — BO delivery in rural beats is structurally harder.

---

## 3. Vertical card labels — every card

Every vertical card (MO, Parcel, IR & GB, CCS, POSB, PLI/RPLI) currently shows two numbers as just "FY27: ₹X Cr" and "Target: ₹Y Cr". Change to:

**Old:**
```
FY27: ₹49.40 Cr
Target: ₹4.12 Cr
```

**New:**
```
Target for FY 2026-27: ₹49.40 Cr
Prop. Target up to Apr-26: ₹4.12 Cr
Difference: ₹45.28 Cr
```

**Notes:**
- The "Prop. Target up to Apr-26" string updates dynamically with the month displayed. When May data is uploaded, it becomes "Prop. Target up to May-26".
- The "Difference" is `(Annual Target − Pro-rata to current month)`.
- Reduce font size of these three lines if vertical space is tight (current card width should accommodate, but smaller font is acceptable).

---

## 4. Vertical contribution — stacked inside division bars

In the **Division ranking horizontal bar chart**, each division's bar should be internally segmented showing each vertical's contribution to that division's total April revenue.

**Behavior:**
- Each bar segments into 6 colored stacks: Parcel + MO + IR & GB + CCS + PLI/RPLI + POSB = 100% of that division's revenue
- Use consistent colors per vertical across the whole dashboard (define once in CSS, reuse everywhere)
- On hover / click: show tooltip with each vertical's absolute ₹ value AND % share of that division
- Show a legend above the chart mapping color → vertical

**Color suggestion (pick what matches design):** keep semantic mapping consistent — e.g., POSB always the same color across Circle/Region/Division views.

---

## 5. Composite Score — move to "Notes" tab

Create a new tab labelled **"Notes"** at the end of the tab row. Move the Composite Score formula explanation there.

**Notes tab content:**

### Composite Score (used on Division views only — Circle view uses % Prop. Achievement instead)

```
For each vertical V in [MO, Parcel, IR&GB, CCS, POSB, PLI/RPLI]:
  pro_rata[V]    = annual_target[V] / 12
  attainment[V]  = (april_actual[V] / pro_rata[V]) × 100

  # POSB special handling — silent + certificate revenue is fully booked in
  # April rather than spread over 12 months. Adjust by 1.5× to neutralize
  # this front-loading and prevent every division showing 150%+ attainment.
  if V == 'POSB':
      attainment[V] = (april_actual[V] / (pro_rata[V] × 1.5)) × 100

target_share[V] = annual_target[V] / Total annual target

composite_score = Σ ( attainment[V] × target_share[V] )
```

**Score bands:**
- ≥ 100 — Strong
- 80–99 — On track
- 60–79 — Needs attention
- < 60 — At risk

**Caveats:**
- Heavily weighted by POSB (66% of typical division target).
- RMS units score artificially low — they don't operate POSB / PLI / RPLI.
- Vijayawada Division can score low despite high absolute revenue because its targets are also the largest.

### Abbreviations

| Abbreviation | Full form |
|--------------|-----------|
| ARPU | Average Revenue Per Unit (₹ per article) |
| BNPL | Buy Now Pay Later (= contractual booking; billed monthly) |
| BPC | Business Post Centre |
| BPO | Branch Post Office |
| CCS | Corporate and Commercial Services |
| ECR | Earnings to Cost Ratio |
| EBO | Excluding Branch Post Offices (in MMU context) |
| FPO | Foreign Post Office |
| HPO | Head Post Office |
| IRGB / IR & GB | International Revenue & Global Business |
| MMU | Mail Monitoring Unit |
| MO | Mail Operations |
| NBP | New Business Premium (insurance) |
| NPH | Nodal Parcel Hub |
| NSH | National Sorting Hub |
| OBO | Only Branch Post Offices (in MMU context) |
| PLI | Postal Life Insurance |
| POPSK | Post Office Passport Seva Kendra |
| POSB | Post Office Savings Bank |
| Prop. | Proportionate (= 1/12 of annual, scaled to current month) |
| RMO | Railway Mail Office |
| RMS | Railway Mail Service |
| RPLI | Rural Postal Life Insurance |
| SPO | Sub Post Office |
| SWAP | Salaries, Wages, Allowances, Pensions |
| TBP | Total Business Premium (NBP + Renewal) |
| TMO | Transit Mail Office |
| VSP | Visakhapatnam (Region abbreviation) |
| VJA | Vijayawada (Region abbreviation) |
| KNL | Kurnool (Region abbreviation) |

### POSB front-loading note
POSB revenue has three components, two of which are booked entirely in April:
- Live Accounts × ₹219.23 per year → pro-rated monthly
- Silent Accounts × ₹35.61 → booked entirely in April (not pro-rated)
- NSC/KVP Certificates × ₹73.92 → booked when issued (continuous)

This is why POSB shows much higher April attainment than other verticals. Not a data error.

### eLekha vs APT
- **APT** (Advanced Postal Technology) measures **business booked at the counter**. Leading indicator.
- **eLekha** measures **revenue actually realized**. Lagging indicator (BNPL bills land 30-60 days after booking).
- Most dashboard numbers are eLekha (realized). Booking-side tab shows APT (leading).

---

## 6. POSB card formatting

Inside the POSB card, the FY 2025-26 Performance line currently shows "OPENED ... CLOSED" on one line. Split:

**Old:**
```
FY 2025-26 PERFORMANCE: OPENED 12,345 CLOSED 8,901
```

**New:**
```
FY 2025-26 Performance:
  Accounts Opened:  12,345
  Accounts Closed:   8,901
```

---

## 7. Sub-division-wise office cards — font sizing

Reduce font size slightly for office names and metric values in the office list cards. Aim for 11px or 10.5px (whichever fits design system).

---

## 8. Month-to-month selector

Add a date-range control to the dashboard header:

**UI:**
```
From: [April-2026 ▼]   To: [April-2026 ▼]
```

**Logic (the critical part — only progressive YTD files are uploaded, so derive month-only data via subtraction):**

```python
# Given two progressive files at end of month_to and at end of (month_from - 1):
selected_data = file[month_to] - file[month_from - 1]

# Examples:
# From=Apr, To=Apr  → data = file[Apr] - file[Mar 2025-26 close] = April-only
# From=Apr, To=Jun  → data = file[Jun] - file[Mar 2025-26 close] = Apr+May+Jun combined
# From=May, To=Jul  → data = file[Jul] - file[Apr] = May+Jun+Jul combined
```

**Display rule:** When `From == To`, all card labels read "for [Month-YY]" (e.g., "for April-26"). When `From != To`, labels read "for [Month-YY] to [Month-YY]".

**Initial state:** Default to From=April-2026, To=April-2026 (until May data uploaded).

**For Phase 2 / Claude Code:** Store each uploaded ECR + SWAP file with its progressive-end month as metadata. The subtraction engine references stored files by month.

---

## 9. Service Quality — MMU upload mechanism

### MMU upload flow

**UI placement:** Add an "Upload" button on the Service Quality tab (or in a settings/admin area).

**Upload flow:**
1. User clicks "Upload MMU Data"
2. Modal opens with:
   - **Date picker** (required) — pick the date the MMU data represents (default: today)
   - File type selector: **MMU - EBOs** or **MMU - OBOs**
   - File upload (CSV)
3. On submit: parse CSV, validate columns, save to database keyed by `(date, type)`
4. **Latest-only display rule:** Service Quality tab always shows the LATEST uploaded date's data. Previous days are stored but not shown by default. No historical trending needed.
5. Display the data date prominently: "MMU data as of [DD-Mon-YYYY]"

**EBO CSV format (expected columns):**
```
S.NO, Region, Division, No.of Articles Invoiced, No.of Articles Delivered,
No.of Articles Returned, No.of Articles Redirected, No.of Articles Kept in Deposit,
Delivery Performance %
```

**OBO CSV format:** Same as EBO.

**Parsing rules:**
- Skip totals row (where Region or Division contains "Total" or is empty)
- Skip region-subtotal rows (where Division equals a region name)
- Treat 29 division rows as the data set

### MMU card display
- Header: "Service Quality — MMU (as of [date])"
- Two side-by-side cards: EBO (Excluding BOs) and OBO (Only BOs)
- Each shows: Delivery Performance %, Invoiced, Delivered, Returned, Redirected, In Deposit
- Color band:
  - EBO: green ≥95%, amber 90-94%, red <90%
  - OBO: green ≥95%, amber 85-94%, red <85% (looser threshold because BO delivery is harder)

---

## 10. NEW: Complaints upload mechanism + display

Same upload pattern as MMU.

### Complaints upload flow

**UI:** "Upload Complaints" button on Service Quality tab.

**Upload modal:**
1. Date picker (required) — pick the date the complaints snapshot represents (default: today)
2. File upload (CSV)
3. On submit: parse, validate, save to DB keyed by date

**Complaints CSV format (expected columns):**
```
Sl., Region, Division, Pending CRM Complaints, Pending PG Portal Complaints,
Pending PG Portal Appeals, Pending Social Media Complaints, Total Pending Complaints
```

**Parsing rules:**
- Skip rows where Division contains "Region", "Circle", "PSD", or matches a region name (those are subtotals/admin)
- Keep only operational division rows (the 33 divisions including RMS units)

### Complaints card display (under Service Quality tab)

**Header:** "Complaints — Pending Status (as of [date])"

**Circle view:** Single tile showing Total Pending across all 4 channels + breakdown:
- Total Pending: [sum]
- CRM: [n]
- PG Portal: [n]
- PG Portal Appeals: [n]
- Social Media: [n]

**Division view:** Per-division row showing the same 5 numbers + rank vs other divisions.

**Color indicator:**
- Green: 0 pending
- Amber: 1-10 pending
- Red: >10 pending
- *(Threshold can be tuned later based on user feedback)*

---

## 11. Date display on Service Quality cards

Both MMU and Complaints cards must display the date of the underlying data prominently. Format: `"as of DD-Mon-YYYY"` (e.g., "as of 20-May-2026").

---

## 12. Implementation notes for Claude Code

### Order of work suggested
1. Add the AP Circle option to the dropdown + create the Circle-level layout (item 1)
2. Global terminology replacements (item 2) — find-and-replace pass
3. Vertical card label restructure (item 3) — touches every card
4. Stacked vertical contribution in division bar chart (item 4)
5. Move Composite Score to new Notes tab (item 5)
6. POSB card layout fix (item 6)
7. Office card font size reduction (item 7)
8. Month-to-month selector with subtraction logic (item 8)
9. MMU upload mechanism + display update (item 9)
10. Complaints upload mechanism + new card (item 10)
11. Final pass: date display on Service Quality cards (item 11), final QA

### Token-saving practices for this build
- Read the current dashboard codebase once at the start; don't re-read for each item
- Make changes in batched commits per logical group (terminology pass = one commit; upload mechanisms = one commit; etc.)
- Use plan mode (`Shift+Tab`) before starting — generate a complete change plan, approve, then execute in one pass
- Skip Opus for find-and-replace items; Sonnet handles items 2, 6, 7, 11 trivially

### What stays unchanged
- Overall visual design (handled in Claude Design separately)
- Card color palette and typography (unless explicitly noted)
- Tab structure within Division view (Overview / Verticals / Booking / POSB & Insurance / Service Quality / Focus Offices / Cost & ECR) — just adding Notes as the 8th tab
- All the underlying data calculations (other than the additions noted)

### Don't introduce
- Historical trending charts for MMU/Complaints (latest-only display by user request)
- Animated/scrubbable timelines
- "Compare divisions" view
- Forecast/projection lines (premature with one month of data)

---

## 13. Data validation checklist for upload mechanisms

For both MMU and Complaints uploads, validate:
- Required columns present (column names exactly as specified)
- All 33 division names match the hierarchy file (warn on mismatch; reject on >2 mismatches)
- Numeric columns parse as integers/floats (reject if not)
- Date picker value is a valid date, not in the future
- File size <2MB
- Same date + same file type combination overwrites previous upload (with confirmation prompt)

---

## 14. Open items deferred to future iterations

These are out of scope for this implementation pass but worth noting in code comments:

- **Month-by-month historical trending** — currently latest-only by user request
- **Complaint resolution time tracking** — only pending count for now
- **Staff (Sanctioned/Working/Vacant) integration** — separate future addition
- **Anomaly engine** — automated rule-based exception detection (planned for next phase)
- **Multi-user auth** — solo operator only for now

---

**End of spec.** Single-pass implementation; if any ambiguity arises during build, default to the existing dashboard's pattern rather than introducing new variants.
