"""Verify the new POSB scheme-wise table renders in BO Lookup."""
from playwright.sync_api import sync_playwright
import time

URL = "http://localhost:8765/index.html"

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1600, "height": 1000})
    page.goto(URL, wait_until="domcontentloaded")
    page.wait_for_timeout(1500)  # let large data parse

    # Open BO Lookup tab
    page.evaluate("showTab('bolookup', document.querySelector('[onclick*=\"bolookup\"]'))")
    page.evaluate("initBOLookup()")
    page.wait_for_timeout(300)

    # Pick the HPO sample (10 schemes) — Amalapuram H.O id 11360042
    page.evaluate("boluSelect('11360042')")
    page.wait_for_timeout(300)
    page.evaluate("boluSub('posb')")
    page.wait_for_timeout(300)

    # Capture scheme table region
    card = page.locator("#bolu-card")
    card.screenshot(path="verify_scheme_table_hpo.png")
    print("Saved verify_scheme_table_hpo.png")

    # Check the table exists and has the expected structure
    sch_table = page.locator(".bolu-scheme-table")
    print("Scheme table count:", sch_table.count())
    if sch_table.count() > 0:
        headers = sch_table.locator("thead th").all_text_contents()
        print("Headers:", headers)
        rows = sch_table.locator("tbody tr").count()
        print("Body rows:", rows)
        for i in range(rows):
            cells = sch_table.locator(f"tbody tr:nth-child({i+1}) td").all_text_contents()
            print(f"Row {i+1}:", cells)

    # Try the BPO with only 3 schemes too
    page.evaluate("boluSelect('11106440')")
    page.wait_for_timeout(300)
    page.evaluate("boluSub('posb')")
    page.wait_for_timeout(300)
    card.screenshot(path="verify_scheme_table_bpo.png")
    print("Saved verify_scheme_table_bpo.png")

    browser.close()
print("Done.")
