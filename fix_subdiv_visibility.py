"""
fix_subdiv_visibility.py
Fixes the sub-division cards not appearing:
1. Prevents bk-subdiv-section from being hidden by the !B forEach loop
2. Wraps renderSubdivBreakdown calls in try/catch
3. Adds defensive visibility reset before each call
"""
import sys

HTML = r"c:\Users\Bhargavi\Documents\Division_Health_Report\Division_Health_Report\index.html"

with open(HTML, encoding="utf-8") as f:
    src = f.read()

changes = 0

# ── Fix 1: !B path forEach — skip bk-subdiv-section ─────────────────────────
# Old: Array.from(bkTab.children).forEach((el, i) => { if (i > 1) el.style.display = 'none'; });
# New: explicitly skip bk-subdiv-section
OLD1 = "    Array.from(bkTab.children).forEach((el, i) => { if (i > 1) el.style.display = 'none'; });"
NEW1 = "    Array.from(bkTab.children).forEach((el, i) => { if (i > 1 && el.id !== 'bk-subdiv-section') el.style.display = 'none'; });"

if OLD1 in src:
    src = src.replace(OLD1, NEW1, 1)
    print("Fix 1 applied: forEach now skips bk-subdiv-section")
    changes += 1
else:
    print("Fix 1: pattern not found (may already be fixed)")

# ── Fix 2: wrap renderSubdivBreakdown in !B path with try/catch + force show ─
OLD2 = "    document.getElementById('booking-count').textContent = '\\u2014';\n    renderSubdivBreakdown(divName);\n    return;"
NEW2 = "    document.getElementById('booking-count').textContent = '\\u2014';\n    const _sdSec = document.getElementById('bk-subdiv-section');\n    if (_sdSec) _sdSec.style.display = '';\n    try { renderSubdivBreakdown(divName); } catch(e) { console.error('[SubDiv]', e); }\n    return;"

if OLD2 in src:
    src = src.replace(OLD2, NEW2, 1)
    print("Fix 2 applied: !B path has explicit show + try/catch")
    changes += 1
else:
    print("Fix 2: pattern not found, trying CRLF variant")
    OLD2c = OLD2.replace("\n", "\r\n")
    NEW2c = NEW2.replace("\n", "\r\n")
    if OLD2c in src:
        src = src.replace(OLD2c, NEW2c, 1)
        print("Fix 2 applied (CRLF)")
        changes += 1
    else:
        print("Fix 2: still not found, skipping")

# ── Fix 3: wrap renderSubdivBreakdown in normal path with try/catch ──────────
OLD3 = "  renderOfficeNetwork(divName);\n  renderOfficeFlags(divName);\n  renderSubdivBreakdown(divName);"
NEW3 = "  renderOfficeNetwork(divName);\n  renderOfficeFlags(divName);\n  const _sdSec2 = document.getElementById('bk-subdiv-section');\n  if (_sdSec2) _sdSec2.style.display = '';\n  try { renderSubdivBreakdown(divName); } catch(e) { console.error('[SubDiv]', e); }"

if OLD3 in src:
    src = src.replace(OLD3, NEW3, 1)
    print("Fix 3 applied: normal path has explicit show + try/catch")
    changes += 1
else:
    OLD3c = OLD3.replace("\n", "\r\n")
    NEW3c = NEW3.replace("\n", "\r\n")
    if OLD3c in src:
        src = src.replace(OLD3c, NEW3c, 1)
        print("Fix 3 applied (CRLF)")
        changes += 1
    else:
        print("Fix 3: pattern not found, skipping")

# ── Fix 4: improve renderSubdivBreakdown to be more defensive ────────────────
# Add console.log trace so developer tools show what's happening
OLD4 = "  window.renderSubdivBreakdown = function(divName) {\n    const section = document.getElementById('bk-subdiv-section');\n    const container = document.getElementById('sd-cards');\n    if (!section || !container) return;"
NEW4 = "  window.renderSubdivBreakdown = function(divName) {\n    const section = document.getElementById('bk-subdiv-section');\n    const container = document.getElementById('sd-cards');\n    if (!section || !container) { console.warn('[SubDiv] section/container missing'); return; }"

if OLD4 in src:
    src = src.replace(OLD4, NEW4, 1)
    print("Fix 4 applied: added warn if section/container missing")
    changes += 1
else:
    OLD4c = OLD4.replace("\n", "\r\n")
    NEW4c = NEW4.replace("\n", "\r\n")
    if OLD4c in src:
        src = src.replace(OLD4c, NEW4c, 1)
        print("Fix 4 applied (CRLF)")
        changes += 1
    else:
        print("Fix 4: skipping")

# Verify key markers still present
assert "SUBDIV_BOOKING" in src, "SUBDIV_BOOKING missing!"
assert "bk-subdiv-section" in src, "HTML placeholder missing!"
assert "renderSubdivBreakdown" in src, "function missing!"

with open(HTML, "w", encoding="utf-8") as f:
    f.write(src)

print(f"\n{changes} fix(es) applied. File saved.")
