HTML = r"c:\Users\Bhargavi\Documents\Division_Health_Report\Division_Health_Report\index.html"

# Open in text mode — Python converts \r\n -> \n on read, \n -> \r\n on write (Windows default)
with open(HTML, encoding="utf-8") as f:
    src = f.read()

# Now src uses \n only (text mode on Windows does CRLF->LF)
START = "if (aggType === 'circle') {"
END_MARKER = "}\n\nfunction renderOverview"

si = src.index(START)
ei = src.index(END_MARKER, si) + 1  # include the closing }

old_block = src[si:ei]
print("Old block length:", len(old_block))
print("Last 60 chars:", repr(old_block[-60:]))

new_block = r"""if (aggType === 'circle') {
    const splitEl = document.getElementById('agg-region-split');
    const regs = ['Vijayawada', 'Visakhapatnam', 'Kurnool'];
    const regData = regs.map(reg => {
      const inReg = members.filter(n => DATA[n].region === reg);
      const inRegVisible = inReg.filter(n => !DATA[n].isOffice);
      const agg = aggregateData(reg, inReg);
      return { reg, agg, inRegVisible, pct: agg.composite_score };
    }).sort((a, b) => b.pct - a.pct);

    splitEl.innerHTML = regData.map(({reg, agg, inRegVisible, pct}, i) => {
      const abbr = REG_ABBR[reg] || reg.substring(0,3).toUpperCase();
      const cls = pct >= 100 ? 'green' : pct >= 80 ? 'amber' : 'red';
      return `
        <div class="region-card">
          <div class="r-rank">#${i+1}</div>
          <h5>${reg} <span class="r-abbr">${abbr}</span></h5>
          <div class="r-sub">${inRegVisible.length} Divisions</div>
          <div class="r-big" style="color:var(--${cls});">${fmt(pct,1)}<span class="pcsym">%</span></div>
          <div class="r-sub" style="font-size:11px; color:var(--${cls}); font-weight:600; margin-bottom:6px;">of proportionate target</div>
          <div class="r-rev">
            <div>FY 2026-27 Target: <strong>₹${fmt(agg.targets.Total,2)} Cr</strong></div>
            <div>April Achievement: <strong>₹${fmt(agg.actuals.Total,2)} Cr</strong></div>
            <div>Prop. Target: <strong>₹${fmt(agg.pro_rata.Total,2)} Cr</strong></div>
          </div>
        </div>`;
    }).join('');
  }
}"""

src = src[:si] + new_block + src[ei:]

# Write back in text mode — Python will convert \n -> \r\n on Windows
with open(HTML, "w", encoding="utf-8") as f:
    f.write(src)

print(f"Saved. New block length={len(new_block)}")
