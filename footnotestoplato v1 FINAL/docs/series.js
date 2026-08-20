/* ===========================================================================
   Footnotes to Plato — series comparison over time
   ---------------------------------------------------------------------------
   Plots attention to named SETS of works across years. One mechanism covers
   every case David asked for, because they differ only in what a set contains:

       "Republic vs Laws"        -> two sets of one work each
       "Plato vs Aristotle"      -> two sets of 36 and 32 works
       "theoretical vs practical"-> two sets from work_groups.json
       "philosophy vs classics"  -> ONE set of works, split by journal field

   Data comes from view_a_filter.json: work -> {citations,articles} -> journal
   -> year -> n. That is FLOOR ONLY (see AGGREGATOR_PATCH.md §2), so every
   curve here is a lower bound. Works whose page numbers collide lose more to
   that floor than others, and unevenly across years; the intro caveat says so
   rather than letting the lines imply completeness. (The old per-work tier
   dashing was retired — its resolution rate rested on alphabetical filing.)

   Honesty constraints baked in:
     - Raw counts by default, but a "share of year" mode, because raw counts
       mostly track how much the journals published that year, not how much
       attention a work got. Both are offered; neither is hidden.
     - Smoothing is opt-in and labelled, never silently applied.
   ======================================================================== */
(function (global) {
  "use strict";

  const NS = "http://www.w3.org/2000/svg";

  const Series = {
    // --- palette: categorical, distinct from the tier/heat colours ---------
    COLORS: ["#5a5497", "#1f9e8a", "#b06a3a", "#8a8f4a", "#8b86c9", "#3a2a7d"],

    /* Build a year -> n series for a set of works under the current filter.
       `matrix` is view_a_filter.json. `journalFilter` optionally restricts to
       a subset of journals (used by the philosophy/classics split).          */
    seriesFor(matrix, works, opts) {
      opts = opts || {};
      const metric = opts.metric === "articles" ? "articles" : "citations";
      const jset = opts.journals || null;      // Set or null = all
      const y0 = opts.y0, y1 = opts.y1;
      const out = {};
      for (const w of works) {
        const m = matrix[w];
        if (!m) continue;
        const table = m[metric];
        if (!table) continue;
        for (const j in table) {
          if (jset && !jset.has(j)) continue;
          const yrs = table[j];
          for (const y in yrs) {
            const yi = +y;
            if (y0 != null && yi < y0) continue;
            if (y1 != null && yi > y1) continue;
            out[yi] = (out[yi] || 0) + yrs[y];
          }
        }
      }
      return out;
    },

    /* Denominator for share mode: total corpus activity per year under the
       same journal/year filter. Without this, a rising curve usually just
       means the journals published more that decade.                         */
    corpusByYear(matrix, opts) {
      opts = opts || {};
      const metric = opts.metric === "articles" ? "articles" : "citations";
      const jset = opts.journals || null;
      const out = {};
      for (const w in matrix) {
        const table = matrix[w][metric];
        if (!table) continue;
        for (const j in table) {
          if (jset && !jset.has(j)) continue;
          const yrs = table[j];
          for (const y in yrs) out[+y] = (out[+y] || 0) + yrs[y];
        }
      }
      return out;
    },

    /* Centred moving average. Opt-in only — the UI labels it when on, because
       a smoothed line invites reading trends that the raw data may not carry,
       especially in the sparse pre-1950 years.                               */
    smooth(series, window) {
      if (!window || window < 2) return series;
      const ys = Object.keys(series).map(Number).sort((a, b) => a - b);
      if (!ys.length) return series;
      const half = Math.floor(window / 2);
      const out = {};
      for (let i = 0; i < ys.length; i++) {
        let sum = 0, n = 0;
        for (let k = -half; k <= half; k++) {
          const y = ys[i] + k;
          if (series[y] != null) { sum += series[y]; n++; }
        }
        out[ys[i]] = n ? sum / n : 0;
      }
      return out;
    },

    /* Render a multi-line chart.
       `lines` = [{label, color, series, note}] where series is {year: n}.   */
    render(host, lines, opts) {
      opts = opts || {};
      host.innerHTML = "";
      const y0 = opts.y0, y1 = opts.y1;
      const shareMode = !!opts.share;

      // union of years actually present, bounded by the filter window
      let lo = Infinity, hi = -Infinity, max = 0;
      for (const L of lines) {
        for (const y in L.series) {
          const yi = +y;
          if (yi < lo) lo = yi;
          if (yi > hi) hi = yi;
          if (L.series[y] > max) max = L.series[y];
        }
      }
      if (!isFinite(lo)) {
        host.innerHTML = `<div class="sc-empty">No data for the current selection.</div>`;
        return;
      }
      if (y0 != null) lo = Math.max(lo, y0);
      if (y1 != null) hi = Math.min(hi, y1);
      max = max || 1;

      const W = host.clientWidth || 1000;
      const H = opts.height || 340;
      // padT is generous on purpose: the SVG is overflow:visible, so a peak at
      // the top of the range otherwise rides up into whatever sits above the
      // chart. The y-scale also gets 8% headroom so the tallest point never
      // renders flush against the top gridline.
      const padL = 58, padR = 16, padT = 30, padB = 42;
      const plotW = W - padL - padR, plotH = H - padT - padB;
      const span = Math.max(1, hi - lo);
      const X = y => padL + ((y - lo) / span) * plotW;
      const headroom = max * 1.08;
      const Y = v => padT + plotH - (v / headroom) * plotH;

      const svg = document.createElementNS(NS, "svg");
      svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
      svg.setAttribute("height", H);
      svg.setAttribute("class", "sc-svg");

      // y grid
      const ticks = niceTicks(max, 4, shareMode);
      for (const t of ticks) {
        const y = Y(t);
        const gl = document.createElementNS(NS, "line");
        gl.setAttribute("class", "sc-grid");
        gl.setAttribute("x1", padL); gl.setAttribute("x2", W - padR);
        gl.setAttribute("y1", y); gl.setAttribute("y2", y);
        svg.appendChild(gl);
        const tx = document.createElementNS(NS, "text");
        tx.setAttribute("class", "sc-tick");
        tx.setAttribute("x", padL - 7); tx.setAttribute("y", y + 3);
        tx.setAttribute("text-anchor", "end");
        tx.textContent = shareMode ? (t * 100).toFixed(t < 0.01 ? 2 : 1) + "%"
                                   : Math.round(t).toLocaleString();
        svg.appendChild(tx);
      }

      // x ticks: decade marks that fall inside the range
      for (let y = Math.ceil(lo / 10) * 10; y <= hi; y += 10) {
        const x = X(y);
        const tk = document.createElementNS(NS, "text");
        tk.setAttribute("class", "sc-tick");
        tk.setAttribute("x", x); tk.setAttribute("y", padT + plotH + 16);
        tk.setAttribute("text-anchor", "middle");
        tk.textContent = y;
        svg.appendChild(tk);
        const vl = document.createElementNS(NS, "line");
        vl.setAttribute("class", "sc-grid faint");
        vl.setAttribute("x1", x); vl.setAttribute("x2", x);
        vl.setAttribute("y1", padT); vl.setAttribute("y2", padT + plotH);
        svg.appendChild(vl);
      }

      // baseline
      const base = document.createElementNS(NS, "line");
      base.setAttribute("class", "sc-axis");
      base.setAttribute("x1", padL); base.setAttribute("x2", W - padR);
      base.setAttribute("y1", padT + plotH); base.setAttribute("y2", padT + plotH);
      svg.appendChild(base);

      // y axis label
      const yl = document.createElementNS(NS, "text");
      yl.setAttribute("class", "sc-axlabel");
      yl.setAttribute("transform", "rotate(-90)");
      yl.setAttribute("x", -(padT + plotH / 2)); yl.setAttribute("y", 14);
      yl.setAttribute("text-anchor", "middle");
      yl.textContent = shareMode ? "share of all citations that year"
                                 : (opts.metric === "articles" ? "distinct articles" : "citations");
      svg.appendChild(yl);

      // lines
      for (const L of lines) {
        const pts = [];
        for (let y = lo; y <= hi; y++) {
          const v = L.series[y];
          if (v == null) continue;            // gap, not zero — don't invent
          pts.push([X(y), Y(v)]);
        }
        if (!pts.length) continue;
        const dPath = pts.map((p, i) => (i ? "L" : "M") + p[0].toFixed(1) + " " + p[1].toFixed(1)).join(" ");
        const path = document.createElementNS(NS, "path");
        path.setAttribute("class", "sc-line");
        path.setAttribute("d", dPath);
        path.setAttribute("stroke", L.color);
        /* Every line counts only placed citations, so every line is a floor —
           a low line can mean "rarely cited" or "much of its traffic could not
           be placed". That distinction is carried by the per-work fade on the
           home chart and stated in the caveat above this chart, rather than by
           a line style here (the old alphabetical-rate dashing was retired). */
        svg.appendChild(path);
      }

      host.appendChild(svg);

      // hover readout: a vertical rule + per-series values at the nearest year
      const read = document.createElement("div");
      read.className = "sc-readout";
      read.innerHTML = `<span class="sc-ryear">—</span>`;
      host.appendChild(read);

      const rule = document.createElementNS(NS, "line");
      rule.setAttribute("class", "sc-rule");
      rule.setAttribute("y1", padT); rule.setAttribute("y2", padT + plotH);
      rule.style.opacity = "0";
      svg.appendChild(rule);

      svg.addEventListener("mousemove", ev => {
        const r = svg.getBoundingClientRect();
        const px = (ev.clientX - r.left) * (W / r.width);
        let y = Math.round(lo + ((px - padL) / plotW) * span);
        y = Math.max(lo, Math.min(hi, y));
        rule.setAttribute("x1", X(y)); rule.setAttribute("x2", X(y));
        rule.style.opacity = "1";
        let html = `<span class="sc-ryear">${y}</span>`;
        for (const L of lines) {
          const v = L.series[y];
          html += `<span class="sc-ritem"><i style="background:${L.color}"></i>` +
                  `${L.label}: <b>${v == null ? "—" : (shareMode ? (v * 100).toFixed(2) + "%" : Math.round(v).toLocaleString())}</b></span>`;
        }
        read.innerHTML = html;
      });
      svg.addEventListener("mouseleave", () => {
        rule.style.opacity = "0";
        read.innerHTML = `<span class="sc-ryear">—</span>`;
      });
    }
  };

  function niceTicks(max, count, share) {
    const raw = max / count;
    const mag = Math.pow(10, Math.floor(Math.log10(raw)));
    const norm = raw / mag;
    const step = (norm >= 5 ? 5 : norm >= 2 ? 2 : 1) * mag;
    const out = [];
    for (let t = 0; t <= max * 1.0001; t += step) out.push(t);
    if (out[out.length - 1] < max) out.push(out[out.length - 1] + step);
    return out;
  }

  global.Series = Series;
})(window);
