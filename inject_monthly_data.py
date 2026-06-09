"""
inject_monthly_data.py
──────────────────────────────────────────────────────────────────────────────
Injects a new month's division data into the multi-month dashboard.

Usage:
    python inject_monthly_data.py <source_html> <month_label>

Examples:
    python inject_monthly_data.py "uploads/AP_Division_Health_Cards_May_2026.html" "May-26"
    python inject_monthly_data.py "uploads/AP_Division_Health_Cards_June_2026.html" "Jun-26"

What it does:
    1. Reads const DATA = {...} from the source HTML
    2. Injects DATA_BY_MONTH["<month>"] = {...}; into index.html
    3. Adds the month as an option in both month-from and month-to selects
    4. Safe to re-run: replaces existing data for the same month label

Month labels follow the pattern: Apr-26, May-26, Jun-26, Jul-26, Aug-26,
Sep-26, Oct-26, Nov-26, Dec-26, Jan-27, Feb-27, Mar-27
"""
import re, sys, json
from pathlib import Path

BASE = Path(__file__).parent
HTML = BASE / "index.html"

MONTH_NAMES = {
    "Apr-26": "April-2026",  "May-26": "May-2026",   "Jun-26": "June-2026",
    "Jul-26": "July-2026",   "Aug-26": "August-2026", "Sep-26": "September-2026",
    "Oct-26": "October-2026","Nov-26": "November-2026","Dec-26": "December-2026",
    "Jan-27": "January-2027","Feb-27": "February-2027","Mar-27": "March-2027",
}
MONTH_ORDER = list(MONTH_NAMES.keys())

# ── Argument handling ─────────────────────────────────────────────────────────
if len(sys.argv) != 3:
    print(__doc__)
    sys.exit(1)

src_path   = Path(sys.argv[1])
month_key  = sys.argv[2]

if not src_path.exists():
    # Try relative to BASE
    src_path = BASE / sys.argv[1]
if not src_path.exists():
    print(f"ERROR: Source file not found: {sys.argv[1]}")
    sys.exit(1)

if month_key not in MONTH_NAMES:
    print(f"ERROR: Unknown month label '{month_key}'. Valid: {', '.join(MONTH_ORDER)}")
    sys.exit(1)

month_display = MONTH_NAMES[month_key]
print(f"Injecting {month_key} ({month_display}) from: {src_path.name}")

# ── Extract DATA JSON from source HTML ───────────────────────────────────────
with open(src_path, encoding="utf-8") as f:
    src_content = f.read()

m = re.search(r'const DATA = (\{.+?\});(?:\n|$)', src_content)
if not m:
    print("ERROR: Could not find 'const DATA = {...};' in source HTML.")
    print("Make sure the source file is a valid AP Division Health Cards HTML.")
    sys.exit(1)

data_json_str = m.group(1)
print(f"  Extracted DATA JSON: {len(data_json_str):,} chars")

# Validate it's valid JSON
try:
    data_obj = json.loads(data_json_str)
    div_count = len([k for k, v in data_obj.items() if isinstance(v, dict) and not v.get('isOffice')])
    print(f"  Divisions found: {div_count}")
except json.JSONDecodeError as e:
    print(f"ERROR: DATA JSON is invalid: {e}")
    sys.exit(1)

# ── Read dashboard HTML ───────────────────────────────────────────────────────
with open(HTML, encoding="utf-8") as f:
    dash = f.read()

if "DATA_BY_MONTH" not in dash:
    print("ERROR: index.html does not contain DATA_BY_MONTH.")
    print("Please ensure patch_multimonth.py has been run first.")
    sys.exit(1)

# ── Inject or replace DATA_BY_MONTH["<month>"] ───────────────────────────────
injection_line = f'DATA_BY_MONTH["{month_key}"] = {data_json_str};\n'
marker         = f'DATA_BY_MONTH["{month_key}"]'

if marker in dash:
    # Replace existing
    existing_pat = re.compile(re.escape(marker) + r'\s*=\s*\{.+?\};\n', re.DOTALL)
    m2 = existing_pat.search(dash)
    if m2:
        dash = dash[:m2.start()] + injection_line + dash[m2.end():]
        print(f"  Replaced existing {month_key} data in index.html")
    else:
        print(f"WARNING: Found marker '{marker}' but couldn't replace. Manual check needed.")
        sys.exit(1)
else:
    # Insert after the DATA_BY_MONTH declaration line
    insert_after = re.search(r'(const DATA_BY_MONTH = \{ "Apr-26": \{.+?\} \};)\n', dash)
    if not insert_after:
        print("ERROR: Could not locate DATA_BY_MONTH declaration to insert after.")
        sys.exit(1)
    insert_pos = insert_after.end()
    dash = dash[:insert_pos] + injection_line + dash[insert_pos:]
    print(f"  Inserted {month_key} data into index.html")

# ── Update month-from and month-to select options ────────────────────────────
option_html = f'<option value="{month_key}">{month_display}</option>'
option_html_selected = f'<option value="{month_key}" selected>{month_display}</option>'

def update_select(html, select_id, month_key, month_display, option_html, option_html_selected):
    # Pattern: the select element with all its options
    pat = re.compile(
        r'(<select id="' + select_id + r'"[^>]*>)(.*?)(</select>)',
        re.DOTALL
    )
    m = pat.search(html)
    if not m:
        return html, False

    open_tag  = m.group(1)
    options   = m.group(2)
    close_tag = m.group(3)

    # Remove selected from all existing options
    options = re.sub(r' selected', '', options)

    # Remove existing option for this month if present
    options = re.sub(
        r'\s*<option value="' + re.escape(month_key) + r'"[^>]*>[^<]*</option>', '', options
    )

    # Determine insertion position (maintain MONTH_ORDER)
    month_idx = MONTH_ORDER.index(month_key)
    # Find the last option that comes before month_key in order
    insert_before = None
    for later_key in MONTH_ORDER[month_idx+1:]:
        later_pat = re.compile(r'<option value="' + re.escape(later_key) + r'"')
        lm = later_pat.search(options)
        if lm:
            insert_before = lm.start()
            break

    if insert_before is not None:
        options = options[:insert_before] + '\n        ' + option_html_selected + options[insert_before:]
    else:
        options = options.rstrip() + '\n        ' + option_html_selected + '\n      '

    new_select = open_tag + options + close_tag
    return html[:m.start()] + new_select + html[m.end():], True

dash, ok1 = update_select(dash, "month-from", month_key, month_display, option_html, option_html_selected)
dash, ok2 = update_select(dash, "month-to",   month_key, month_display, option_html, option_html_selected)

if ok1 and ok2:
    print(f"  month-from and month-to selects updated with {month_display} (selected)")
else:
    print(f"WARNING: Could not update month selects (ok1={ok1}, ok2={ok2})")

# ── Update CUR_MONTH_LABEL default ───────────────────────────────────────────
old_label = re.search(r"let CUR_MONTH_LABEL = '([^']+)';", dash)
if old_label:
    dash = dash.replace(f"let CUR_MONTH_LABEL = '{old_label.group(1)}';",
                        f"let CUR_MONTH_LABEL = '{month_key}';")
    print(f"  CUR_MONTH_LABEL updated to '{month_key}'")

# ── Write output ─────────────────────────────────────────────────────────────
with open(HTML, "w", encoding="utf-8") as f:
    f.write(dash)

print(f"\nDone. Open index.html — month selector now includes {month_display}.")
print(f"Dashboard defaults to {month_key} view (May-only, derived from Apr cumulative).")
