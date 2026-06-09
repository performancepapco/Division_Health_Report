HTML = r"c:\Users\Bhargavi\Documents\Division_Health_Report\Division_Health_Report\index.html"

with open(HTML, encoding="utf-8") as f:
    src = f.read()

# Find the div-rank rendering block
OLD = """  const rankEl = document.getElementById('agg-div-rank');
  const maxComp = Math.max(...divs.map(x => x.composite), 100);
  rankEl.innerHTML = divs.map((x, i) => {
    const cls = x.composite >= 90 ? 'green' : x.composite >= 60 ? 'amber' : 'red';
    const w = Math.min(x.composite / maxComp * 100, 100);
    return `
      <div class="div-rank-row">
        <div class="r-num">${String(i+1).padStart(2,'0')}</div>
        <div class="r-name">${x.name}<span class="r-region">${REG_ABBR[x.region] || x.region.substring(0,3).toUpperCase()}</span></div>
        <div class="r-bar"><div class="r-fill ${cls}" style="width:${w}%;"></div></div>
        <div class="r-pct ${cls}">${fmt(x.composite,1)}%</div>
        <div class="r-rev">\\u20b9${fmt(x.actuals,2)} Cr</div>
      </div>`;
  }).join('');"""

if OLD not in src:
    print("OLD pattern not found, checking variants...")
    # try to find the rank block differently
    idx = src.find("const rankEl = document.getElementById('agg-div-rank')")
    if idx == -1:
        print("rankEl not found at all!")
    else:
        print("Found rankEl at:", idx)
        print(repr(src[idx:idx+600]))
else:
    NEW = """  // VERT_CFG: vertical colors for stacked bar
  const VERT_CFG = [
    { key:'Mail Operations', label:'MO',       cls:'seg-mo'      },
    { key:'Parcel',          label:'Parcel',    cls:'seg-parcel'  },
    { key:'IR & GB',         label:'IR & GB',  cls:'seg-irgb'    },
    { key:'CCS',             label:'CCS',       cls:'seg-ccs'     },
    { key:'POSB',            label:'POSB',      cls:'seg-posb'    },
    { key:'PLI/RPLI',        label:'PLI/RPLI', cls:'seg-plirpli' },
  ];

  // Populate legend
  const legendEl = document.getElementById('div-rank-legend');
  legendEl.style.display = '';
  legendEl.innerHTML = VERT_CFG.map(v =>
    `<span class="legend-item"><span class="legend-swatch ${v.cls}"></span>${v.label}</span>`
  ).join('');

  const rankEl = document.getElementById('agg-div-rank');
  const maxComp = Math.max(...divs.map(x => x.composite), 100);
  rankEl.innerHTML = divs.map((x, i) => {
    const cls = x.composite >= 90 ? 'green' : x.composite >= 60 ? 'amber' : 'red';
    const w = Math.min(x.composite / maxComp * 100, 100);
    const divActuals = DATA[x.name]?.actuals || {};
    const totalRev = x.actuals || 1;
    const segs = VERT_CFG.map(vc => {
      const val = divActuals[vc.key] || 0;
      const segW = (val / totalRev) * w;
      const pctShare = (val / totalRev * 100).toFixed(1);
      return `<div class="r-seg ${vc.cls}" style="width:${segW}%;" title="${vc.label}: \\u20b9${fmt(val,2)} Cr (${pctShare}%)"></div>`;
    }).join('');
    return `
      <div class="div-rank-row">
        <div class="r-num">${String(i+1).padStart(2,'0')}</div>
        <div class="r-name">${x.name}<span class="r-region">${REG_ABBR[x.region] || x.region.substring(0,3).toUpperCase()}</span></div>
        <div class="r-bar">${segs}</div>
        <div class="r-pct ${cls}">${fmt(x.composite,1)}%</div>
        <div class="r-rev">\\u20b9${fmt(x.actuals,2)} Cr</div>
      </div>`;
  }).join('');"""

    src = src.replace(OLD, NEW, 1)
    with open(HTML, "w", encoding="utf-8") as f:
        f.write(src)
    print("Stacked bar patch applied.")
