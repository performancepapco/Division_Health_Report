"""
inject_subdiv.py
Injects the Sub-Division Booking Breakdown feature into index.html.
Safe to re-run: checks for existing injection markers before inserting.
"""
import json, re, sys

BASE   = r"c:\Users\Bhargavi\Documents\Division_Health_Report\Division_Health_Report"
HTML   = BASE + r"\index.html"
SDFILE = BASE + r"\_subdiv_booking.json"

with open(SDFILE, encoding="utf-8") as f:
    sd_json = f.read().strip()

with open(HTML, encoding="utf-8") as f:
    src = f.read()

# ── Guard ─────────────────────────────────────────────────────────────────────
if "SUBDIV_BOOKING" in src:
    print("Already injected — nothing to do.")
    sys.exit(0)

# ══════════════════════════════════════════════════════════════════════════════
# 1. CSS — insert before </style>
# ══════════════════════════════════════════════════════════════════════════════
NEW_CSS = r"""
/* ============ SUB-DIVISION BOOKING BREAKDOWN ============ */
.sd-section-goal {
  background: oklch(0.14 0.04 258);
  border-left: 4px solid var(--accent);
  padding: 12px 18px;
  margin-bottom: 20px;
  font-family: var(--font-mono);
  font-size: 13px;
  letter-spacing: 0.06em;
  color: oklch(0.82 0.04 80);
  display: flex;
  align-items: center;
  gap: 12px;
}
.sd-section-goal strong { color: var(--accent); }
.sd-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(420px, 1fr));
  gap: 18px;
  margin-top: 4px;
}
.sd-card {
  background: var(--paper);
  border: 1px solid var(--rule);
  border-top: 3px solid var(--ink-strong);
  display: flex;
  flex-direction: column;
}
.sd-card-header {
  background: var(--ink-strong);
  padding: 12px 16px 10px;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
}
.sd-card-title {
  font-family: var(--font-serif);
  font-size: 17px;
  font-weight: 600;
  color: var(--paper);
  line-height: 1.2;
  font-variation-settings: "opsz" 20;
}
.sd-card-badges {
  display: flex;
  gap: 6px;
  flex-shrink: 0;
  align-items: center;
}
.sd-badge {
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.08em;
  padding: 2px 7px;
  border-radius: 2px;
  text-transform: uppercase;
}
.sd-badge.ho { background: oklch(0.46 0.10 245 / 0.25); color: var(--blue); border: 1px solid oklch(0.46 0.10 245 / 0.4); }
.sd-badge.so { background: oklch(0.62 0.12 75 / 0.25); color: var(--amber); border: 1px solid oklch(0.62 0.12 75 / 0.4); }
.sd-badge.bo { background: oklch(0.48 0.14 25 / 0.2); color: var(--red); border: 1px solid oklch(0.48 0.14 25 / 0.35); }
.sd-nil-warn {
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.1em;
  color: var(--red);
  background: oklch(0.48 0.14 25 / 0.18);
  border: 1px solid oklch(0.48 0.14 25 / 0.35);
  padding: 2px 7px;
  border-radius: 2px;
}
/* inner tabs */
.sd-tabs {
  display: flex;
  border-bottom: 1px solid var(--rule-strong);
  background: var(--paper-warm);
}
.sd-tab {
  font-family: var(--font-mono);
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  padding: 9px 16px 7px;
  cursor: pointer;
  border: 0;
  background: transparent;
  color: var(--ink-soft);
  border-bottom: 2px solid transparent;
  position: relative;
  bottom: -1px;
  transition: color 0.15s;
}
.sd-tab:hover { color: var(--ink); }
.sd-tab.active {
  color: var(--ink-strong);
  border-bottom-color: var(--accent);
  background: var(--paper);
}
.sd-tab .sd-tab-nil {
  display: inline-block;
  background: var(--red);
  color: #fff;
  font-size: 9px;
  padding: 1px 4px;
  border-radius: 2px;
  margin-left: 4px;
  vertical-align: middle;
  font-weight: 700;
}
/* tab panels */
.sd-panel { display: none; padding: 14px 16px 16px; }
.sd-panel.active { display: block; }
/* bucket band */
.sd-buckets {
  display: flex;
  gap: 0;
  margin-bottom: 14px;
  border: 1px solid var(--rule);
  overflow: hidden;
  border-radius: 3px;
}
.sd-bucket {
  flex: 1;
  padding: 8px 6px 6px;
  text-align: center;
  border-right: 1px solid var(--rule);
  cursor: default;
}
.sd-bucket:last-child { border-right: 0; }
.sd-bucket.bk-nil  { background: oklch(0.94 0.035 25); }
.sd-bucket.bk-low  { background: oklch(0.96 0.03 50); }
.sd-bucket.bk-mid  { background: oklch(0.96 0.03 78); }
.sd-bucket.bk-high { background: oklch(0.96 0.025 120); }
.sd-bucket.bk-top  { background: oklch(0.94 0.03 155); }
.sd-bk-count {
  font-family: var(--font-serif);
  font-size: 22px;
  font-weight: 600;
  line-height: 1;
  font-variation-settings: "opsz" 24;
}
.sd-bucket.bk-nil  .sd-bk-count { color: var(--red); }
.sd-bucket.bk-low  .sd-bk-count { color: oklch(0.52 0.13 35); }
.sd-bucket.bk-mid  .sd-bk-count { color: var(--amber); }
.sd-bucket.bk-high .sd-bk-count { color: oklch(0.50 0.10 115); }
.sd-bucket.bk-top  .sd-bk-count { color: var(--green); }
.sd-bk-label {
  font-family: var(--font-mono);
  font-size: 9.5px;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--ink-soft);
  margin-top: 3px;
}
.sd-bk-articles {
  font-family: var(--font-mono);
  font-size: 9px;
  color: var(--ink-faint);
  margin-top: 1px;
}
/* office rows */
.sd-office-list { font-size: 0; }
.sd-office-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 5px 0;
  border-bottom: 1px solid var(--rule);
  font-size: 14px;
}
.sd-office-row:last-child { border-bottom: 0; }
.sd-office-row .sd-or-num {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--ink-faint);
  min-width: 22px;
  text-align: right;
}
.sd-office-row .sd-or-name {
  font-family: var(--font-sans);
  font-size: 13px;
  color: var(--ink);
  flex: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.sd-office-row .sd-or-arts {
  font-family: var(--font-mono);
  font-size: 12px;
  font-weight: 700;
  padding: 2px 7px;
  border-radius: 2px;
  min-width: 52px;
  text-align: center;
}
.sd-or-arts.bk-nil  { background: oklch(0.94 0.035 25); color: var(--red); }
.sd-or-arts.bk-low  { background: oklch(0.96 0.03 50); color: oklch(0.52 0.13 35); }
.sd-or-arts.bk-mid  { background: oklch(0.96 0.03 78); color: var(--amber); }
.sd-or-arts.bk-high { background: oklch(0.96 0.025 120); color: oklch(0.50 0.10 115); }
.sd-or-arts.bk-top  { background: oklch(0.94 0.03 155); color: var(--green); }
.sd-office-row .sd-or-rev {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--ink-soft);
  min-width: 72px;
  text-align: right;
}
/* show more button */
.sd-more-btn {
  margin-top: 10px;
  width: 100%;
  padding: 8px;
  background: var(--paper-warm);
  border: 1px solid var(--rule);
  font-family: var(--font-mono);
  font-size: 11.5px;
  letter-spacing: 0.08em;
  color: var(--ink-soft);
  cursor: pointer;
  text-align: center;
  text-transform: uppercase;
  transition: background 0.15s;
}
.sd-more-btn:hover { background: var(--paper-deep); color: var(--ink); }
.sd-more-btn[data-state="expanded"] { color: var(--ink-faint); }
.sd-hidden-rows { display: none; }
.sd-hidden-rows.expanded { display: contents; }
/* empty sub-div name */
.sd-anon { color: oklch(0.82 0.04 80); font-style: italic; }
"""

assert "</style>" in src, "Could not find </style>"
src = src.replace("</style>", NEW_CSS + "\n</style>", 1)
print("CSS injected.")

# ══════════════════════════════════════════════════════════════════════════════
# 2. HTML — add placeholder inside tab-booking, near the end
# ══════════════════════════════════════════════════════════════════════════════
SD_HTML = """
  <!-- ===== SUB-DIVISION BOOKING BREAKDOWN ===== -->
  <div id="bk-subdiv-section">
    <div class="section-head" style="margin-top: 36px;">
      <h2>Sub-Division Booking Breakdown</h2>
      <span class="desc">Office-level article distribution<br>HO / SO / BO by sub-division</span>
    </div>
    <div class="sd-section-goal">
      <strong>&#x25B6; Goal:</strong>&nbsp;Move NIL offices to 1–5 articles, 1–5 to 6–10, and 6–10 to above 10 per month. Every activated office compounds circle revenue.
    </div>
    <div class="sd-grid" id="sd-cards"></div>
  </div>
"""

BOOKING_TAB_END = '</div>\n\n<!-- ===== POSB & INSURANCE TAB'
assert BOOKING_TAB_END in src, "Could not find booking tab closing marker"
src = src.replace(BOOKING_TAB_END, SD_HTML + '\n</div>\n\n<!-- ===== POSB & INSURANCE TAB', 1)
print("HTML placeholder injected.")

# ══════════════════════════════════════════════════════════════════════════════
# 3. JS — embed data + render function, before the closing </script>
# ══════════════════════════════════════════════════════════════════════════════
SD_JS = r"""
// ============ SUB-DIVISION BOOKING DATA ============
const SUBDIV_BOOKING = """ + sd_json + r""";

// ============ SUB-DIVISION BOOKING RENDER ============
(function() {

  /* Bucket definitions per office type */
  const BUCKETS = {
    HOs: [
      { cls: 'bk-nil',  label: '< 100',    test: a => a < 100 },
      { cls: 'bk-low',  label: '100–300',  test: a => a >= 100 && a < 300 },
      { cls: 'bk-mid',  label: '300–500',  test: a => a >= 300 && a < 500 },
      { cls: 'bk-high', label: '> 500',    test: a => a >= 500 },
    ],
    SOs: [
      { cls: 'bk-nil',  label: 'NIL',      test: a => a === 0 },
      { cls: 'bk-low',  label: '1–10',     test: a => a >= 1 && a <= 10 },
      { cls: 'bk-mid',  label: '11–30',    test: a => a >= 11 && a <= 30 },
      { cls: 'bk-high', label: '31–50',    test: a => a >= 31 && a <= 50 },
      { cls: 'bk-top',  label: '> 50',     test: a => a > 50 },
    ],
    BOs: [
      { cls: 'bk-nil',  label: 'NIL',      test: a => a === 0 },
      { cls: 'bk-low',  label: '1–5',      test: a => a >= 1 && a <= 5 },
      { cls: 'bk-mid',  label: '6–10',     test: a => a >= 6 && a <= 10 },
      { cls: 'bk-high', label: '11–20',    test: a => a >= 11 && a <= 20 },
      { cls: 'bk-top',  label: '> 20',     test: a => a > 20 },
    ],
  };

  function bucketCls(slotKey, articles) {
    const bs = BUCKETS[slotKey];
    for (const b of bs) { if (b.test(articles)) return b.cls; }
    return 'bk-top';
  }

  function fmtRev(r) {
    if (r >= 1e5) return '₹' + (r/1e5).toFixed(1) + 'L';
    if (r >= 1e3) return '₹' + (r/1e3).toFixed(1) + 'K';
    return r > 0 ? '₹' + Math.round(r) : '—';
  }

  function buildPanel(offices, slotKey, cardId, sdIdx) {
    if (!offices || offices.length === 0) {
      return '<div style="color:var(--ink-faint); font-style:italic; font-size:13px; padding: 8px 0;">No offices of this type in this sub-division.</div>';
    }
    // sorted ascending already from Python
    const bs = BUCKETS[slotKey];

    // — bucket band —
    const bucketCounts = bs.map(b => ({
      ...b,
      count: offices.filter(o => b.test(o.articles)).length,
      arts:  offices.filter(o => b.test(o.articles)).reduce((s,o)=>s+o.articles,0),
    }));
    const bandHtml = '<div class="sd-buckets">' +
      bucketCounts.map(b => `
        <div class="sd-bucket ${b.cls}">
          <div class="sd-bk-count">${b.count}</div>
          <div class="sd-bk-label">${b.label}</div>
          <div class="sd-bk-articles">${b.arts > 0 ? b.arts.toLocaleString() + ' art' : ''}</div>
        </div>`).join('') +
      '</div>';

    // — office rows —
    const INITIAL = 10;
    const makeRow = (o, idx) => {
      const cls = bucketCls(slotKey, o.articles);
      const artLabel = o.articles === 0 ? 'NIL' : o.articles.toLocaleString();
      return `
        <div class="sd-office-row">
          <span class="sd-or-num">${String(idx+1).padStart(2,'0')}</span>
          <span class="sd-or-name" title="${o.name}">${o.name}</span>
          <span class="sd-or-arts ${cls}">${artLabel}</span>
          <span class="sd-or-rev">${fmtRev(o.revenue)}</span>
        </div>`;
    };

    const visible = offices.slice(0, INITIAL);
    const hidden  = offices.slice(INITIAL);
    const moreId  = `sd-more-${cardId}-${slotKey}`;
    const rowsId  = `sd-rows-${cardId}-${slotKey}`;

    let html = bandHtml + '<div class="sd-office-list">';
    html += visible.map((o, i) => makeRow(o, i)).join('');
    if (hidden.length > 0) {
      html += `<div id="${rowsId}" class="sd-hidden-rows">${hidden.map((o, i) => makeRow(o, INITIAL + i)).join('')}</div>`;
    }
    html += '</div>';
    if (hidden.length > 0) {
      html += `<button class="sd-more-btn" data-state="collapsed" data-rows="${rowsId}" data-more="${moreId}"
        onclick="sdToggleMore(this)">&#x25BC; Show ${hidden.length} more offices</button>`;
    }
    return html;
  }

  function buildCard(sdName, slots, cardId) {
    const displayName = sdName || '<em class="sd-anon">Unassigned</em>';

    // count NIL offices across all types
    const nilCount = ['HOs','SOs','BOs'].reduce((s, k) => {
      return s + ((slots[k] || []).filter(o => o.articles === 0).length);
    }, 0);

    const hoCnt = (slots.HOs || []).length;
    const soCnt = (slots.SOs || []).length;
    const boCnt = (slots.BOs || []).length;
    const total = hoCnt + soCnt + boCnt;
    if (total === 0) return '';

    const nilBadge = nilCount > 0
      ? `<span class="sd-nil-warn">NIL: ${nilCount}</span>` : '';

    const tabs = [
      { key: 'HOs', label: 'HOs', count: hoCnt },
      { key: 'SOs', label: 'SOs', count: soCnt },
      { key: 'BOs', label: 'BOs', count: boCnt },
    ].filter(t => t.count > 0);

    const firstTab = tabs[0]?.key || 'HOs';

    const tabButtons = tabs.map(t => {
      const nilInTab = (slots[t.key] || []).filter(o => o.articles === 0).length;
      const nilTag = nilInTab > 0 ? `<span class="sd-tab-nil">${nilInTab}</span>` : '';
      return `<button class="sd-tab${t.key === firstTab ? ' active' : ''}" onclick="sdSwitchTab(this,'${cardId}','${t.key}')">${t.label}${nilTag} <span style="font-size:10px; opacity:0.6;">(${t.count})</span></button>`;
    }).join('');

    const panels = tabs.map(t =>
      `<div class="sd-panel${t.key === firstTab ? ' active' : ''}" id="sdp-${cardId}-${t.key}">
        ${buildPanel(slots[t.key] || [], t.key, cardId, 0)}
       </div>`
    ).join('');

    return `
      <div class="sd-card" id="sdc-${cardId}">
        <div class="sd-card-header">
          <div class="sd-card-title">${displayName}</div>
          <div class="sd-card-badges">
            ${hoCnt > 0 ? `<span class="sd-badge ho">HO ${hoCnt}</span>` : ''}
            ${soCnt > 0 ? `<span class="sd-badge so">SO ${soCnt}</span>` : ''}
            ${boCnt > 0 ? `<span class="sd-badge bo">BO ${boCnt}</span>` : ''}
            ${nilBadge}
          </div>
        </div>
        <div class="sd-tabs">${tabButtons}</div>
        ${panels}
      </div>`;
  }

  window.renderSubdivBreakdown = function(divName) {
    const section = document.getElementById('bk-subdiv-section');
    const container = document.getElementById('sd-cards');
    if (!section || !container) return;

    // Only show for individual division views
    if (!divName || divName.startsWith('__')) {
      section.style.display = 'none';
      return;
    }

    const divData = SUBDIV_BOOKING[divName];
    if (!divData) {
      section.style.display = 'none';
      return;
    }

    section.style.display = '';
    const sdNames = Object.keys(divData).sort((a,b) => {
      // put empty-name last
      if (!a) return 1; if (!b) return -1;
      return a.localeCompare(b);
    });

    let html = '';
    sdNames.forEach((sd, idx) => {
      html += buildCard(sd, divData[sd], divName.replace(/\s+/g,'_') + '_' + idx);
    });
    container.innerHTML = html || '<div class="placeholder">No sub-division data for this division.</div>';
  };

}());

// Toggle sub-division inner tabs
function sdSwitchTab(btn, cardId, slotKey) {
  const card = document.getElementById('sdc-' + cardId);
  if (!card) return;
  card.querySelectorAll('.sd-tab').forEach(t => t.classList.remove('active'));
  card.querySelectorAll('.sd-panel').forEach(p => p.classList.remove('active'));
  btn.classList.add('active');
  const panel = document.getElementById('sdp-' + cardId + '-' + slotKey);
  if (panel) panel.classList.add('active');
}

// Toggle "show more" rows
function sdToggleMore(btn) {
  const rowsId = btn.dataset.rows;
  const el = document.getElementById(rowsId);
  if (!el) return;
  if (btn.dataset.state === 'collapsed') {
    el.classList.add('expanded');
    btn.dataset.state = 'expanded';
    btn.textContent = '▲ Show less';
  } else {
    el.classList.remove('expanded');
    btn.dataset.state = 'collapsed';
    const n = el.children.length;
    btn.textContent = '▼ Show ' + n + ' more offices';
  }
}
"""

# Insert just before the initial render call
RENDER_ANCHOR = "// Initial render\nrenderDivision('__CIRCLE__');"
assert RENDER_ANCHOR in src, "Could not find render anchor"
src = src.replace(RENDER_ANCHOR, SD_JS + "\n" + RENDER_ANCHOR, 1)
print("JS injected.")

# ══════════════════════════════════════════════════════════════════════════════
# 4. Wire renderSubdivBreakdown into renderBooking
# ══════════════════════════════════════════════════════════════════════════════
WIRE_TARGET = "  renderOfficeNetwork(divName);\n  renderOfficeFlags(divName);"
WIRE_REPLACE = "  renderOfficeNetwork(divName);\n  renderOfficeFlags(divName);\n  renderSubdivBreakdown(divName);"
assert WIRE_TARGET in src, "Could not find renderOfficeNetwork call"
src = src.replace(WIRE_TARGET, WIRE_REPLACE, 1)
print("renderSubdivBreakdown wired into renderBooking.")

# ── Write ─────────────────────────────────────────────────────────────────────
with open(HTML, "w", encoding="utf-8") as f:
    f.write(src)

final_kb = len(src.encode("utf-8")) / 1024
print(f"\nDone. index.html is now {final_kb:.0f} KB ({final_kb/1024:.1f} MB)")
