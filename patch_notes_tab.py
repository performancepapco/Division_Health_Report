HTML = r"c:\Users\Bhargavi\Documents\Division_Health_Report\Division_Health_Report\index.html"

with open(HTML, encoding="utf-8") as f:
    src = f.read()

# 1. Add Notes tab button after Cost & ECR button
OLD_BTN = """  <button class="tab" onclick="showTab('cost', this)">Cost &amp; ECR</button>
</div>"""

NEW_BTN = """  <button class="tab" onclick="showTab('cost', this)">Cost &amp; ECR</button>
  <button class="tab" onclick="showTab('notes', this)">Notes</button>
</div>"""

if OLD_BTN not in src:
    print("Tab button marker not found!")
else:
    src = src.replace(OLD_BTN, NEW_BTN, 1)
    print("Tab button added.")

# 2. Add Notes tab content before </body>
NOTES_TAB = """
<!-- ===== NOTES TAB ===== -->
<div id="tab-notes" class="tab-content">
  <div class="section-head">
    <h2>Notes &amp; Definitions</h2>
    <span class="desc">Reference material for this dashboard</span>
  </div>

  <!-- Composite Score formula -->
  <div class="card-box" style="max-width:760px; margin-bottom:28px;">
    <h4>Composite Score <span style="font-size:12px; font-weight:500; color:var(--ink-soft);">(used on Division views only — Circle view uses % Prop. Achievement)</span></h4>
    <pre style="font-family:var(--font-mono); font-size:12px; line-height:1.7; background:var(--paper-warm); padding:14px 16px; border-radius:4px; overflow-x:auto; white-space:pre-wrap;">For each vertical V in [MO, Parcel, IR&amp;GB, CCS, POSB, PLI/RPLI]:
  pro_rata[V]    = annual_target[V] / 12
  attainment[V]  = (april_actual[V] / pro_rata[V]) × 100

  # POSB special handling — silent + certificate revenue is fully booked in
  # April rather than spread over 12 months. Adjust by 1.5× to neutralise
  # this front-loading and prevent every division showing 150%+ attainment.
  if V == 'POSB':
      attainment[V] = (april_actual[V] / (pro_rata[V] × 1.5)) × 100

target_share[V] = annual_target[V] / Total annual target

composite_score = Σ ( attainment[V] × target_share[V] )</pre>
    <p style="font-size:12.5px; margin-top:10px; color:var(--ink-soft);">
      <strong>Score bands:</strong>&nbsp;
      <span style="color:var(--green);">≥ 100 — Strong</span>&nbsp;·&nbsp;
      <span>80–99 — On track</span>&nbsp;·&nbsp;
      <span style="color:var(--amber);">60–79 — Needs attention</span>&nbsp;·&nbsp;
      <span style="color:var(--red);">&lt; 60 — At risk</span>
    </p>
    <p style="font-size:12px; color:var(--ink-faint); margin-top:8px;">
      <strong>Caveats:</strong> Heavily weighted by POSB (66% of typical division target).
      RMS units score artificially low — they don't operate POSB / PLI / RPLI.
      Vijayawada Division can score low despite high absolute revenue because its targets are also the largest.
    </p>
  </div>

  <!-- Abbreviations -->
  <div class="card-box" style="margin-bottom:28px;">
    <h4>Abbreviations</h4>
    <table class="brief" style="max-width:640px;">
      <thead><tr><th>Abbr.</th><th>Full Form</th></tr></thead>
      <tbody>
        <tr><td>ARPU</td><td>Average Revenue Per Unit (₹ per article)</td></tr>
        <tr><td>BNPL</td><td>Buy Now Pay Later (contractual booking; billed monthly)</td></tr>
        <tr><td>BPC</td><td>Business Post Centre</td></tr>
        <tr><td>BPO</td><td>Branch Post Office</td></tr>
        <tr><td>CCS</td><td>Corporate and Commercial Services</td></tr>
        <tr><td>ECR</td><td>Earnings to Cost Ratio</td></tr>
        <tr><td>EBO</td><td>Excluding Branch Post Offices (in MMU context)</td></tr>
        <tr><td>FPO</td><td>Foreign Post Office</td></tr>
        <tr><td>HPO</td><td>Head Post Office</td></tr>
        <tr><td>IRGB / IR &amp; GB</td><td>International Revenue &amp; Global Business</td></tr>
        <tr><td>MMU</td><td>Mail Monitoring Unit</td></tr>
        <tr><td>MO</td><td>Mail Operations</td></tr>
        <tr><td>NBP</td><td>New Business Premium (insurance)</td></tr>
        <tr><td>NPH</td><td>Nodal Parcel Hub</td></tr>
        <tr><td>NSH</td><td>National Sorting Hub</td></tr>
        <tr><td>OBO</td><td>Only Branch Post Offices (in MMU context)</td></tr>
        <tr><td>PLI</td><td>Postal Life Insurance</td></tr>
        <tr><td>POPSK</td><td>Post Office Passport Seva Kendra</td></tr>
        <tr><td>POSB</td><td>Post Office Savings Bank</td></tr>
        <tr><td>Prop.</td><td>Proportionate (= 1/12 of annual, scaled to current month)</td></tr>
        <tr><td>RMO</td><td>Railway Mail Office</td></tr>
        <tr><td>RMS</td><td>Railway Mail Service</td></tr>
        <tr><td>RPLI</td><td>Rural Postal Life Insurance</td></tr>
        <tr><td>SPO</td><td>Sub Post Office</td></tr>
        <tr><td>SWAP</td><td>Salaries, Wages, Allowances, Pensions</td></tr>
        <tr><td>TBP</td><td>Total Business Premium (NBP + Renewal)</td></tr>
        <tr><td>TMO</td><td>Transit Mail Office</td></tr>
        <tr><td>VSP</td><td>Visakhapatnam (Region abbreviation)</td></tr>
        <tr><td>VJA</td><td>Vijayawada (Region abbreviation)</td></tr>
        <tr><td>KNL</td><td>Kurnool (Region abbreviation)</td></tr>
      </tbody>
    </table>
  </div>

  <!-- POSB front-loading note -->
  <div class="card-box" style="max-width:680px; margin-bottom:28px;">
    <h4>POSB Revenue Front-loading</h4>
    <p style="font-size:13px; line-height:1.7;">POSB revenue has three components, two of which are booked entirely in April:</p>
    <ul style="font-size:12.5px; line-height:1.8; color:var(--ink-soft); padding-left:20px;">
      <li>Live Accounts × ₹219.23 per year → <strong>pro-rated monthly</strong></li>
      <li>Silent Accounts × ₹35.61 → <strong>booked entirely in April</strong> (not pro-rated)</li>
      <li>NSC/KVP Certificates × ₹73.92 → booked when issued (continuous)</li>
    </ul>
    <p style="font-size:12px; color:var(--ink-faint); margin-top:8px;">This is why POSB shows much higher April attainment than other verticals. Not a data error.</p>
  </div>

  <!-- eLekha vs APT -->
  <div class="card-box" style="max-width:680px; margin-bottom:28px;">
    <h4>eLekha vs APT</h4>
    <table class="brief" style="max-width:600px;">
      <thead><tr><th>System</th><th>What it measures</th><th>Nature</th></tr></thead>
      <tbody>
        <tr><td><strong>APT</strong></td><td>Business booked at the counter</td><td style="color:var(--green);">Leading indicator</td></tr>
        <tr><td><strong>eLekha</strong></td><td>Revenue actually realised</td><td style="color:var(--amber);">Lagging indicator (BNPL bills land 30–60 days after booking)</td></tr>
      </tbody>
    </table>
    <p style="font-size:12px; color:var(--ink-faint); margin-top:8px;">Most dashboard numbers are eLekha (realised). The Booking tab shows APT (leading).</p>
  </div>
</div>"""

if "</body>" in src:
    src = src.replace("</body>", NOTES_TAB + "\n</body>", 1)
    print("Notes tab content added before </body>.")
else:
    print("</body> not found!")

with open(HTML, "w", encoding="utf-8") as f:
    f.write(src)

print("Done.")
