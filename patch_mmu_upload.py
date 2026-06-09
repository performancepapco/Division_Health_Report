HTML = r"c:\Users\Bhargavi\Documents\Division_Health_Report\Division_Health_Report\index.html"

with open(HTML, encoding="utf-8") as f:
    src = f.read()

changes = 0

# ── 1. Add upload bar + date badge before mmu-content ──
OLD1 = '  <div id="mmu-content"></div>'
NEW1 = '''  <div class="upload-bar" style="margin-bottom:8px;">
    <button class="upload-btn" onclick="openMmuUpload()">Upload MMU Data</button>
    <span id="mmu-data-date" class="data-date"></span>
  </div>
  <div id="mmu-content"></div>'''
if OLD1 in src:
    src = src.replace(OLD1, NEW1, 1)
    print("1: mmu upload bar added")
    changes += 1
else:
    print("1: mmu-content pattern not found!")

# ── 2. Add upload bar + complaints div for complaints section ──
OLD2 = '''  <div class="section-head" style="margin-top: 32px;">
    <h2>Complaints</h2>
    <span class="desc">Centralized Customer Care data</span>
  </div>
  <div class="placeholder">'''
NEW2 = '''  <div class="section-head" style="margin-top: 32px;">
    <h2>Complaints</h2>
    <span class="desc">Centralized Customer Care data</span>
  </div>
  <div class="upload-bar" style="margin-bottom:8px;">
    <button class="upload-btn" onclick="openComplaintsUpload()">Upload Complaints Data</button>
    <span id="complaints-data-date" class="data-date"></span>
  </div>
  <div id="complaints-content"></div>
  <div class="placeholder" id="complaints-placeholder">'''
if OLD2 in src:
    src = src.replace(OLD2, NEW2, 1)
    print("2: complaints upload bar added")
    changes += 1
else:
    print("2: complaints placeholder not found, checking...")
    idx = src.find('<h2>Complaints</h2>')
    if idx != -1:
        print("  Found complaints h2 at:", idx)
        print("  Context:", repr(src[idx:idx+200]))

# ── 3. Update renderService signature to accept divName ──
OLD3 = 'function renderService(d) {'
NEW3 = 'function renderService(d, divName) {'
if OLD3 in src:
    src = src.replace(OLD3, NEW3, 1)
    print("3: renderService signature updated")
    changes += 1
else:
    print("3: renderService signature not found!")

# ── 4. Update renderDivision call to pass divName ──
OLD4 = '  renderService(d);'
NEW4 = '  renderService(d, divName);'
if OLD4 in src:
    src = src.replace(OLD4, NEW4, 1)
    print("4: renderService call updated")
    changes += 1
else:
    print("4: renderService call not found!")

# ── 5. Update renderService body to use localStorage MMU data + date display ──
OLD5 = '''function renderService(d, divName) {
  const el = document.getElementById('mmu-content');
  if (!d.mmu.ebo && !d.mmu.obo) {
    el.innerHTML = '<div class="placeholder"><strong>No MMU data for this division</strong></div>';
    return;
  }
  let html = '<div class="delivery-block">';
  if (d.mmu.ebo) {
    const e = d.mmu.ebo;'''

NEW5 = '''function renderService(d, divName) {
  const el = document.getElementById('mmu-content');

  // Prefer localStorage MMU data over embedded DATA
  const lsEbo = JSON.parse(localStorage.getItem('mmu_ebo') || 'null');
  const lsObo = JSON.parse(localStorage.getItem('mmu_obo') || 'null');
  let mmuEbo = d.mmu?.ebo;
  let mmuObo = d.mmu?.obo;
  let eboDate = null, oboDate = null;

  if (lsEbo) {
    const key = divName;
    if (d.isAggregate) {
      // Aggregate: sum up all member divisions
      const memberNames = d.aggMembers || Object.keys(DATA);
      let sumI=0, sumDl=0, sumR=0, sumRd=0, sumDp=0;
      let any = false;
      memberNames.forEach(n => {
        const x = lsEbo.byDivision[n]; if (!x) return; any=true;
        sumI+=x.Invoiced||0; sumDl+=x.Delivered||0; sumR+=x.Returned||0; sumRd+=x.Redirected||0; sumDp+=x.Deposit||0;
      });
      mmuEbo = any ? { Invoiced:sumI, Delivered:sumDl, Returned:sumR, Redirected:sumRd, Deposit:sumDp, DP:sumI>0?sumDl/sumI*100:0 } : null;
    } else {
      mmuEbo = lsEbo.byDivision[key] || null;
    }
    eboDate = lsEbo.date;
  }
  if (lsObo) {
    const key = divName;
    if (d.isAggregate) {
      const memberNames = d.aggMembers || Object.keys(DATA);
      let sumI=0, sumDl=0, sumR=0, sumRd=0, sumDp=0;
      let any = false;
      memberNames.forEach(n => {
        const x = lsObo.byDivision[n]; if (!x) return; any=true;
        sumI+=x.Invoiced||0; sumDl+=x.Delivered||0; sumR+=x.Returned||0; sumRd+=x.Redirected||0; sumDp+=x.Deposit||0;
      });
      mmuObo = any ? { Invoiced:sumI, Delivered:sumDl, Returned:sumR, Redirected:sumRd, Deposit:sumDp, DP:sumI>0?sumDl/sumI*100:0 } : null;
    } else {
      mmuObo = lsObo.byDivision[key] || null;
    }
    oboDate = lsObo.date;
  }

  // Update date badge
  const dateBadge = document.getElementById('mmu-data-date');
  if (dateBadge) {
    const dateStr = eboDate || oboDate;
    dateBadge.textContent = dateStr ? 'Data as of ' + fmtDate(dateStr) : '';
  }

  if (!mmuEbo && !mmuObo) {
    el.innerHTML = '<div class="placeholder"><strong>No MMU data for this division</strong></div>';
    renderComplaints(d, divName);
    return;
  }
  const mmuHeader = (eboDate || oboDate) ? ` (as of ${fmtDate(eboDate || oboDate)})` : '';
  let html = '<h4 style="font-size:13px; font-weight:600; margin-bottom:12px;">Service Quality — MMU' + mmuHeader + '</h4>';
  html += '<div class="delivery-block">';
  if (mmuEbo) {
    const e = mmuEbo;'''

if OLD5 in src:
    src = src.replace(OLD5, NEW5, 1)
    print("5: renderService body updated with localStorage support")
    changes += 1
else:
    print("5: renderService body pattern not found, checking...")
    idx = src.find('function renderService(d, divName)')
    if idx != -1:
        print("  renderService found at:", idx)
        print("  Next 300 chars:", repr(src[idx:idx+300]))

# ── 6. Update mmu.ebo/mmu.obo references inside renderService ──
# Change d.mmu.ebo and d.mmu.obo references to mmuEbo/mmuObo in the render block
# Find the second occurrence of 'if (d.mmu.obo)' (first is now 'if (mmuObo)')
OLD6a = '''  if (d.mmu.obo) {
    const o = d.mmu.obo;'''
NEW6a = '''  if (mmuObo) {
    const o = mmuObo;'''
if OLD6a in src:
    src = src.replace(OLD6a, NEW6a, 1)
    print("6a: mmu.obo reference updated")
    changes += 1
else:
    print("6a: mmu.obo reference not found")

OLD6b = '''  } else {
    html += '<div class="delivery-stat"><h5>OBO — no data</h5></div>';
  }'''
# Only replace first occurrence (in renderService, not elsewhere)
if OLD6b in src:
    src = src.replace(OLD6b, '''  } else {
    html += '<div class="delivery-stat"><h5>OBO — no data</h5></div>';
  }''', 1)  # no change needed, keep as is
    print("6b: OBO else block found (no change needed)")

# Update mmu.ebo caveat references
OLD6c = '  if (d.mmu.obo && d.mmu.obo.DP < 90) {'
NEW6c = '  if (mmuObo && mmuObo.DP < 90) {'
if OLD6c in src:
    src = src.replace(OLD6c, NEW6c, 1)
    print("6c: mmuObo caveat updated")
    changes += 1

OLD6d = '    html += `<div class="caveat" style="border-left-color:var(--red);"><strong>OBO delivery alert —</strong> ${fmt(d.mmu.obo.DP,2)}% is below 90% threshold.'
NEW6d = '    html += `<div class="caveat" style="border-left-color:var(--red);"><strong>OBO delivery alert —</strong> ${fmt(mmuObo.DP,2)}% is below 90% threshold.'
if OLD6d in src:
    src = src.replace(OLD6d, NEW6d, 1)
    print("6d: OBO alert message updated")
    changes += 1

OLD6e = '${fmtInt(d.mmu.obo.Invoiced - d.mmu.obo.Delivered)}'
NEW6e = '${fmtInt(mmuObo.Invoiced - mmuObo.Delivered)}'
if OLD6e in src:
    src = src.replace(OLD6e, NEW6e, 1)
    print("6e: OBO article diff updated")
    changes += 1

OLD6f = '${fmtInt(d.mmu.obo.Invoiced)}'
NEW6f = '${fmtInt(mmuObo.Invoiced)}'
if OLD6f in src:
    src = src.replace(OLD6f, NEW6f, 1)
    print("6f: OBO invoiced updated")
    changes += 1

OLD6g = '  if (d.mmu.ebo && d.mmu.ebo.DP < 95) {'
NEW6g = '  if (mmuEbo && mmuEbo.DP < 95) {'
if OLD6g in src:
    src = src.replace(OLD6g, NEW6g, 1)
    print("6g: mmuEbo caveat updated")
    changes += 1

OLD6h = '    html += `<div class="caveat"><strong>EBO delivery flag —</strong> ${fmt(d.mmu.ebo.DP,2)}%'
NEW6h = '    html += `<div class="caveat"><strong>EBO delivery flag —</strong> ${fmt(mmuEbo.DP,2)}%'
if OLD6h in src:
    src = src.replace(OLD6h, NEW6h, 1)
    print("6h: EBO alert message updated")
    changes += 1

# ── 7. Add renderComplaints call at end of renderService ──
OLD7 = '''  el.innerHTML = html;
}

function renderFocus'''
NEW7 = '''  el.innerHTML = html;
  renderComplaints(d, divName);
}

function renderFocus'''
if OLD7 in src:
    src = src.replace(OLD7, NEW7, 1)
    print("7: renderComplaints call added at end of renderService")
    changes += 1
else:
    print("7: renderService end pattern not found")

# ── 8. Add upload modal HTML + fmtDate + upload JS functions before </body> ──
UPLOAD_CODE = '''
<!-- ===== MMU UPLOAD MODAL ===== -->
<div id="mmu-modal" class="modal-overlay" style="display:none;" onclick="if(event.target===this)closeMmuModal()">
  <div class="modal-box">
    <h3>Upload MMU Data</h3>
    <div class="modal-field">
      <label>Data date <span class="req">*</span></label>
      <input type="date" id="mmu-upload-date" max="">
    </div>
    <div class="modal-field">
      <label>File type <span class="req">*</span></label>
      <select id="mmu-upload-type">
        <option value="ebo">MMU — EBOs (Excluding Branch Post Offices)</option>
        <option value="obo">MMU — OBOs (Only Branch Post Offices)</option>
      </select>
    </div>
    <div class="modal-field">
      <label>CSV file <span class="req">*</span></label>
      <input type="file" id="mmu-upload-file" accept=".csv">
    </div>
    <div id="mmu-upload-error" class="upload-error"></div>
    <div class="modal-actions">
      <button class="btn-primary" onclick="submitMmuUpload()">Upload</button>
      <button class="btn-secondary" onclick="closeMmuModal()">Cancel</button>
    </div>
  </div>
</div>

<!-- ===== COMPLAINTS UPLOAD MODAL ===== -->
<div id="complaints-modal" class="modal-overlay" style="display:none;" onclick="if(event.target===this)closeComplaintsModal()">
  <div class="modal-box">
    <h3>Upload Complaints Data</h3>
    <div class="modal-field">
      <label>Data date <span class="req">*</span></label>
      <input type="date" id="complaints-upload-date" max="">
    </div>
    <div class="modal-field">
      <label>CSV file <span class="req">*</span></label>
      <input type="file" id="complaints-upload-file" accept=".csv">
    </div>
    <div id="complaints-upload-error" class="upload-error"></div>
    <div class="modal-actions">
      <button class="btn-primary" onclick="submitComplaintsUpload()">Upload</button>
      <button class="btn-secondary" onclick="closeComplaintsModal()">Cancel</button>
    </div>
  </div>
</div>

<script>
// ── Date formatter ──────────────────────────────────────────────────────────
function fmtDate(isoDate) {
  if (!isoDate) return '';
  const d = new Date(isoDate + 'T00:00:00');
  const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  return String(d.getDate()).padStart(2,'0') + '-' + months[d.getMonth()] + '-' + d.getFullYear();
}

// ── CSV parser ──────────────────────────────────────────────────────────────
function parseCSV(text) {
  const lines = text.replace(/\\r\\n/g,'\\n').replace(/\\r/g,'\\n').trim().split('\\n');
  if (!lines.length) return { headers: [], rows: [] };
  const headers = lines[0].split(',').map(h => h.trim().replace(/^"|"$/g,''));
  const rows = lines.slice(1).map(line => {
    const vals = line.split(',').map(v => v.trim().replace(/^"|"$/g,''));
    const obj = {};
    headers.forEach((h, i) => { obj[h] = vals[i] || ''; });
    return obj;
  });
  return { headers, rows };
}

// ── MMU Upload ──────────────────────────────────────────────────────────────
function openMmuUpload() {
  const today = new Date().toISOString().slice(0,10);
  document.getElementById('mmu-upload-date').max = today;
  document.getElementById('mmu-upload-date').value = today;
  document.getElementById('mmu-upload-file').value = '';
  document.getElementById('mmu-upload-error').textContent = '';
  document.getElementById('mmu-modal').style.display = 'flex';
}
function closeMmuModal() {
  document.getElementById('mmu-modal').style.display = 'none';
}

const MMU_REQUIRED_COLS = [
  'S.NO','Region','Division','No.of Articles Invoiced','No.of Articles Delivered',
  'No.of Articles Returned','No.of Articles Redirected',
  'No.of Articles Kept in Deposit','Delivery Performance %'
];

function submitMmuUpload() {
  const errEl = document.getElementById('mmu-upload-error');
  errEl.textContent = '';
  const dateVal = document.getElementById('mmu-upload-date').value;
  const typeVal = document.getElementById('mmu-upload-type').value;
  const fileEl  = document.getElementById('mmu-upload-file');

  if (!dateVal) { errEl.textContent = 'Please select a date.'; return; }
  if (new Date(dateVal) > new Date()) { errEl.textContent = 'Date cannot be in the future.'; return; }
  if (!fileEl.files.length) { errEl.textContent = 'Please select a CSV file.'; return; }
  const file = fileEl.files[0];
  if (file.size > 2 * 1024 * 1024) { errEl.textContent = 'File too large (max 2MB).'; return; }

  const existing = JSON.parse(localStorage.getItem('mmu_' + typeVal) || 'null');
  if (existing && existing.date === dateVal) {
    if (!confirm('Data for this date and type already exists. Overwrite?')) return;
  }

  const reader = new FileReader();
  reader.onload = function(e) {
    try {
      const { headers, rows } = parseCSV(e.target.result);
      // Validate columns
      const missing = MMU_REQUIRED_COLS.filter(c => !headers.includes(c));
      if (missing.length) { errEl.textContent = 'Missing columns: ' + missing.join(', '); return; }
      // Parse rows
      const byDivision = {};
      let parsed = 0, skipped = 0;
      rows.forEach(row => {
        const div = (row['Division'] || '').trim();
        const reg = (row['Region'] || '').trim();
        if (!div || /total/i.test(div) || /total/i.test(reg) || div === reg) { skipped++; return; }
        const inv  = parseFloat(row['No.of Articles Invoiced']) || 0;
        const del  = parseFloat(row['No.of Articles Delivered']) || 0;
        const ret  = parseFloat(row['No.of Articles Returned']) || 0;
        const redir= parseFloat(row['No.of Articles Redirected']) || 0;
        const dep  = parseFloat(row['No.of Articles Kept in Deposit']) || 0;
        const dp   = parseFloat(row['Delivery Performance %']) || (inv > 0 ? del/inv*100 : 0);
        byDivision[div] = { Invoiced:inv, Delivered:del, Returned:ret, Redirected:redir, Deposit:dep, DP:dp };
        parsed++;
      });
      if (parsed === 0) { errEl.textContent = 'No valid division rows found in CSV.'; return; }
      localStorage.setItem('mmu_' + typeVal, JSON.stringify({ date: dateVal, byDivision }));
      closeMmuModal();
      // Re-render current division service tab
      const badge = document.getElementById('mmu-data-date');
      if (badge) badge.textContent = 'Data as of ' + fmtDate(dateVal);
      renderDivision(CUR_DIV_NAME);
    } catch(ex) {
      errEl.textContent = 'Parse error: ' + ex.message;
    }
  };
  reader.readAsText(file);
}

// ── Complaints Upload ───────────────────────────────────────────────────────
function openComplaintsUpload() {
  const today = new Date().toISOString().slice(0,10);
  document.getElementById('complaints-upload-date').max = today;
  document.getElementById('complaints-upload-date').value = today;
  document.getElementById('complaints-upload-file').value = '';
  document.getElementById('complaints-upload-error').textContent = '';
  document.getElementById('complaints-modal').style.display = 'flex';
}
function closeComplaintsModal() {
  document.getElementById('complaints-modal').style.display = 'none';
}

const COMPLAINTS_REQUIRED_COLS = [
  'Sl.','Region','Division','Pending CRM Complaints','Pending PG Portal Complaints',
  'Pending PG Portal Appeals','Pending Social Media Complaints','Total Pending Complaints'
];
const COMPLAINTS_REGION_NAMES = new Set(['Vijayawada','Visakhapatnam','Kurnool',
  'Vijayawada Region','Visakhapatnam Region','Kurnool Region','AP Circle','Circle']);

function submitComplaintsUpload() {
  const errEl = document.getElementById('complaints-upload-error');
  errEl.textContent = '';
  const dateVal = document.getElementById('complaints-upload-date').value;
  const fileEl  = document.getElementById('complaints-upload-file');

  if (!dateVal) { errEl.textContent = 'Please select a date.'; return; }
  if (new Date(dateVal) > new Date()) { errEl.textContent = 'Date cannot be in the future.'; return; }
  if (!fileEl.files.length) { errEl.textContent = 'Please select a CSV file.'; return; }
  const file = fileEl.files[0];
  if (file.size > 2 * 1024 * 1024) { errEl.textContent = 'File too large (max 2MB).'; return; }

  const existing = JSON.parse(localStorage.getItem('complaints') || 'null');
  if (existing && existing.date === dateVal) {
    if (!confirm('Complaints data for this date already exists. Overwrite?')) return;
  }

  const reader = new FileReader();
  reader.onload = function(e) {
    try {
      const { headers, rows } = parseCSV(e.target.result);
      const missing = COMPLAINTS_REQUIRED_COLS.filter(c => !headers.includes(c));
      if (missing.length) { errEl.textContent = 'Missing columns: ' + missing.join(', '); return; }
      const byDivision = {};
      let parsed = 0;
      rows.forEach(row => {
        const div = (row['Division'] || '').trim();
        const reg = (row['Region'] || '').trim();
        if (!div || COMPLAINTS_REGION_NAMES.has(div) || COMPLAINTS_REGION_NAMES.has(reg)
            || /region/i.test(div) || /circle/i.test(div) || /psd/i.test(div)) return;
        const crm    = parseInt(row['Pending CRM Complaints']) || 0;
        const pg     = parseInt(row['Pending PG Portal Complaints']) || 0;
        const pgApp  = parseInt(row['Pending PG Portal Appeals']) || 0;
        const sm     = parseInt(row['Pending Social Media Complaints']) || 0;
        const total  = parseInt(row['Total Pending Complaints']) || (crm + pg + pgApp + sm);
        byDivision[div] = { crm, pg, pgApp, sm, total };
        parsed++;
      });
      if (parsed === 0) { errEl.textContent = 'No valid division rows found.'; return; }
      localStorage.setItem('complaints', JSON.stringify({ date: dateVal, byDivision }));
      closeComplaintsModal();
      const badge = document.getElementById('complaints-data-date');
      if (badge) badge.textContent = 'Data as of ' + fmtDate(dateVal);
      renderDivision(CUR_DIV_NAME);
    } catch(ex) {
      errEl.textContent = 'Parse error: ' + ex.message;
    }
  };
  reader.readAsText(file);
}

// ── Render Complaints section ───────────────────────────────────────────────
function renderComplaints(d, divName) {
  const el = document.getElementById('complaints-content');
  const ph = document.getElementById('complaints-placeholder');
  if (!el) return;

  const lsC = JSON.parse(localStorage.getItem('complaints') || 'null');
  const badge = document.getElementById('complaints-data-date');

  if (!lsC) {
    el.innerHTML = '';
    if (ph) ph.style.display = '';
    return;
  }

  if (ph) ph.style.display = 'none';
  if (badge) badge.textContent = 'Data as of ' + fmtDate(lsC.date);

  const dateHeader = `Complaints — Pending Status (as of ${fmtDate(lsC.date)})`;

  if (d.isAggregate) {
    // Circle/region view: aggregate totals
    const memberNames = d.aggMembers || Object.keys(DATA);
    let tot={crm:0,pg:0,pgApp:0,sm:0,total:0};
    memberNames.forEach(n => {
      const x = lsC.byDivision[n]; if (!x) return;
      tot.crm+=x.crm||0; tot.pg+=x.pg||0; tot.pgApp+=x.pgApp||0; tot.sm+=x.sm||0; tot.total+=x.total||0;
    });
    const cls = tot.total === 0 ? 'green' : tot.total <= 10 ? 'amber' : 'red';
    el.innerHTML = `
      <h4 style="font-size:13px; font-weight:600; margin-bottom:10px;">${dateHeader}</h4>
      <div class="kpi-row cols-4" style="margin-top:8px;">
        <div class="kpi feature">
          <div><div class="kpi-label">Total Pending</div>
          <div class="kpi-value" style="color:var(--${cls});">${tot.total}</div></div>
          <div class="kpi-sub">All channels combined</div>
        </div>
        <div class="kpi"><div><div class="kpi-label">CRM</div><div class="kpi-value">${tot.crm}</div></div></div>
        <div class="kpi"><div><div class="kpi-label">PG Portal</div><div class="kpi-value">${tot.pg}</div></div>
          <div class="kpi-sub">Appeals: ${tot.pgApp}</div></div>
        <div class="kpi"><div><div class="kpi-label">Social Media</div><div class="kpi-value">${tot.sm}</div></div></div>
      </div>`;
  } else {
    // Division view
    const x = lsC.byDivision[divName];
    if (!x) {
      el.innerHTML = `<h4 style="font-size:13px; font-weight:600; margin-bottom:10px;">${dateHeader}</h4><div class="placeholder">No complaints data for this division</div>`;
      return;
    }
    const cls = x.total === 0 ? 'green' : x.total <= 10 ? 'amber' : 'red';
    el.innerHTML = `
      <h4 style="font-size:13px; font-weight:600; margin-bottom:10px;">${dateHeader}</h4>
      <div class="kpi-row cols-4" style="margin-top:8px;">
        <div class="kpi feature">
          <div><div class="kpi-label">Total Pending</div>
          <div class="kpi-value" style="color:var(--${cls});">${x.total}</div></div>
          <div class="kpi-sub"><span class="tag ${cls}">${x.total===0?'Clear':x.total<=10?'Watch':'Action needed'}</span></div>
        </div>
        <div class="kpi"><div><div class="kpi-label">CRM</div><div class="kpi-value">${x.crm}</div></div></div>
        <div class="kpi"><div><div class="kpi-label">PG Portal</div><div class="kpi-value">${x.pg}</div></div>
          <div class="kpi-sub">Appeals: ${x.pgApp}</div></div>
        <div class="kpi"><div><div class="kpi-label">Social Media</div><div class="kpi-value">${x.sm}</div></div></div>
      </div>`;
  }
}

// ── On page load: restore badges from localStorage ──────────────────────────
(function restoreUploadBadges() {
  const lsEbo = JSON.parse(localStorage.getItem('mmu_ebo') || 'null');
  const lsObo = JSON.parse(localStorage.getItem('mmu_obo') || 'null');
  const lsC   = JSON.parse(localStorage.getItem('complaints') || 'null');
  const mmuDate = (lsEbo || lsObo) ? fmtDate((lsEbo || lsObo).date) : null;
  if (mmuDate) {
    const b = document.getElementById('mmu-data-date');
    if (b) b.textContent = 'Data as of ' + mmuDate;
  }
  if (lsC) {
    const b = document.getElementById('complaints-data-date');
    if (b) b.textContent = 'Data as of ' + fmtDate(lsC.date);
  }
})();
</script>'''

if '</body>' in src:
    src = src.replace('</body>', UPLOAD_CODE + '\n</body>', 1)
    print("8: upload modals + JS added before </body>")
    changes += 1
else:
    print("8: </body> not found!")

with open(HTML, "w", encoding="utf-8") as f:
    f.write(src)

print(f"\nTotal changes applied: {changes}")
