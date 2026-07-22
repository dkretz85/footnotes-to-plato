/* ===========================================================================
   Footnotes to Plato — shared filter bar
   ---------------------------------------------------------------------------
   ONE implementation used by both views, so the two can never drift apart.

   Renders:
     - 10 journal checkboxes (+ all / none), each with its corpus-wide count
     - a two-handle year range slider, 1887–2022, with a volume sparkline
       behind it showing the year histogram (75%+ of citations are post-1980,
       so the sparkline is what makes the early tail legible)

   Contract with the host view:
     FilterBar.mount(el, meta, onChange)   -> renders, calls onChange(state)
     FilterBar.state                       -> {journals:Set, y0:int, y1:int}
     FilterBar.matches(d)                  -> true if a dot passes the filter
     FilterBar.isDefault()                 -> true if nothing is narrowed

   The host decides what to recompute. This module owns no data.
   ======================================================================== */
(function (global) {
  "use strict";

  const NS = "http://www.w3.org/2000/svg";

  const FilterBar = {
    state: { journals: new Set(), y0: 1887, y1: 2022 },
    _meta: null,
    _onChange: null,
    _el: null,
    _allJournals: [],

    mount(el, meta, onChange, groups) {
      this._el = el;
      this._meta = meta;
      this._onChange = onChange || function () {};
      this._allJournals = meta.journals.slice();
      this._groups = groups || null;
      // default: everything on, full year range (an honest "no filter" start)
      this.state.journals = new Set(this._allJournals);
      this.state.y0 = meta.year_min;
      this.state.y1 = meta.year_max;
      this._render();
      return this;
    },

    // which group a journal belongs to; "other" if unclassified
    groupOf(j) {
      if (!this._groups) return "other";
      for (const k in this._groups.groups) {
        if (this._groups.groups[k].journals.indexOf(j) >= 0) return k;
      }
      return "other";
    },

    // journals in a group, busiest first
    _groupJournals(k) {
      const counts = this._meta.journal_counts || {};
      return this._allJournals
        .filter(j => this.groupOf(j) === k)
        .sort((a, b) => (counts[b] || 0) - (counts[a] || 0));
    },

    isDefault() {
      return this.state.journals.size === this._allJournals.length &&
             this.state.y0 === this._meta.year_min &&
             this.state.y1 === this._meta.year_max;
    },

    // does one citation ("dot") survive the current filter?
    matches(d) {
      if (!this.state.journals.has(d.journal)) return false;
      const y = +d.year;
      if (!y) return true;            // undated: never silently dropped
      return y >= this.state.y0 && y <= this.state.y1;
    },

    _fire() {
      this._updateSummary();
      this._onChange(this.state);
    },

    // ---- markup -----------------------------------------------------------
    _render() {
      const m = this._meta;
      const el = this._el;
      el.className = "filterbar";
      el.innerHTML = `
        <div class="fb-head">
          <div class="fb-title">Filter</div>
          <div class="fb-summary" id="fbSummary"></div>
          <button class="fb-reset" id="fbReset">Reset</button>
        </div>
        <div class="fb-body">
          <div class="fb-col fb-journals">
            <div class="fb-label">Journals
              <span class="fb-mini fb-allsel"><button data-all="1">all</button> ·
              <button data-all="0">none</button></span>
            </div>
            <div class="fb-groups" id="fbJournals"></div>
            <div class="fb-cnote">Counts are that journal's total citations of
              <em>any</em> work in the corpus — its overall weight, not its
              citations of the work shown below.</div>
          </div>
          <div class="fb-col fb-years">
            <div class="fb-label">Years
              <span class="fb-range" id="fbRange"></span>
            </div>
            <div class="fb-slider" id="fbSlider">
              <div class="fb-spark" id="fbSpark"></div>
              <div class="fb-track"><div class="fb-sel" id="fbSel"></div></div>
              <input type="range" id="fbY0" min="${m.year_min}" max="${m.year_max}" value="${m.year_min}">
              <input type="range" id="fbY1" min="${m.year_min}" max="${m.year_max}" value="${m.year_max}">
            </div>
            <div class="fb-ticks">
              <span>${m.year_min}</span><span>1950</span><span>1990</span><span>${m.year_max}</span>
            </div>
          </div>
        </div>`;

      this._buildJournals();
      this._buildSpark();
      this._wireSlider();
      this._updateSummary();

      el.querySelector("#fbReset").addEventListener("click", () => {
        this.state.journals = new Set(this._allJournals);
        this.state.y0 = m.year_min; this.state.y1 = m.year_max;
        el.querySelector("#fbY0").value = m.year_min;
        el.querySelector("#fbY1").value = m.year_max;
        this._syncChecks();
        this._syncGroupStates();
        this._syncSlider();
        this._fire();
      });

      for (const b of el.querySelectorAll(".fb-allsel button")) {
        b.addEventListener("click", () => {
          const on = b.dataset.all === "1";
          this.state.journals = on ? new Set(this._allJournals) : new Set();
          this._syncChecks();
          this._syncGroupStates();
          this._fire();
        });
      }
    },

    _buildJournals() {
      const host = this._el.querySelector("#fbJournals");
      const counts = this._meta.journal_counts || {};
      host.innerHTML = "";

      // group order: as declared in journal_groups.json, then any stragglers
      let keys;
      if (this._groups) {
        keys = Object.keys(this._groups.groups);
        const loose = this._allJournals.filter(j => this.groupOf(j) === "other");
        if (loose.length) keys.push("other");
      } else {
        keys = ["other"];
      }

      for (const k of keys) {
        const js = this._groupJournals(k);
        if (!js.length) continue;
        const label = (this._groups && this._groups.groups[k])
          ? this._groups.groups[k].label : "Other";
        const tot = js.reduce((a, j) => a + (counts[j] || 0), 0);

        const col = document.createElement("div");
        col.className = "fb-group";
        col.innerHTML =
          `<div class="fb-ghead">` +
            `<span class="fb-gname">${label}</span>` +
            `<span class="fb-gtot">${tot.toLocaleString()}</span>` +
            `<span class="fb-mini fb-gsel">` +
              `<button data-g="${k}" data-on="1">all</button> · ` +
              `<button data-g="${k}" data-on="0">none</button>` +
            `</span>` +
          `</div>`;
        const list = document.createElement("div");
        list.className = "fb-glist";

        for (const j of js) {
          const lab = document.createElement("label");
          lab.className = "fb-j";
          lab.innerHTML =
            `<input type="checkbox" checked data-j="${j.replace(/"/g, '&quot;')}">` +
            `<span class="fb-jn" title="${j}">${j}</span>` +
            `<span class="fb-jc">${(counts[j] || 0).toLocaleString()}</span>`;
          const cb = lab.querySelector("input");
          cb.addEventListener("change", () => {
            if (cb.checked) this.state.journals.add(j);
            else this.state.journals.delete(j);
            this._syncGroupStates();
            this._fire();
          });
          list.appendChild(lab);
        }
        col.appendChild(list);

        // per-group all/none
        for (const b of col.querySelectorAll(".fb-gsel button")) {
          b.addEventListener("click", () => {
            const on = b.dataset.on === "1";
            for (const j of this._groupJournals(b.dataset.g)) {
              if (on) this.state.journals.add(j); else this.state.journals.delete(j);
            }
            this._syncChecks();
            this._syncGroupStates();
            this._fire();
          });
        }
        host.appendChild(col);
      }
      this._syncGroupStates();
    },

    // reflect state back onto the checkboxes (after group/all/none/reset)
    _syncChecks() {
      for (const cb of this._el.querySelectorAll(".fb-j input")) {
        cb.checked = this.state.journals.has(cb.dataset.j);
      }
    },

    // dim a group header when none of its journals are selected
    _syncGroupStates() {
      const heads = this._el.querySelectorAll(".fb-group");
      let i = 0;
      const keys = this._groups ? Object.keys(this._groups.groups) : ["other"];
      for (const k of keys) {
        const js = this._groupJournals(k);
        if (!js.length) continue;
        const el = heads[i++];
        if (!el) continue;
        const n = js.filter(j => this.state.journals.has(j)).length;
        el.classList.toggle("off", n === 0);
        el.classList.toggle("partial", n > 0 && n < js.length);
      }
    },

    // volume sparkline behind the slider: makes the pre-1950 thinness visible
    // so a narrow early window doesn't look like a bug.
    _buildSpark() {
      const m = this._meta;
      let hist = m.year_histogram;
      if (typeof hist === "string") {           // aggregator may emit a py-repr
        try { hist = JSON.parse(hist.replace(/'/g, '"')); } catch (e) { hist = {}; }
      }
      const y0 = m.year_min, y1 = m.year_max, span = y1 - y0;
      let max = 0;
      for (const k in hist) if (hist[k] > max) max = hist[k];
      max = Math.max(max, 1);

      const svg = document.createElementNS(NS, "svg");
      svg.setAttribute("viewBox", `0 0 ${span + 1} 100`);
      svg.setAttribute("preserveAspectRatio", "none");
      svg.setAttribute("class", "fb-sparksvg");
      // area path, sqrt-scaled so the thin early years stay visible
      let dPath = `M 0 100`;
      for (let y = y0; y <= y1; y++) {
        const v = hist[y] || hist[String(y)] || 0;
        const h = Math.sqrt(v) / Math.sqrt(max) * 96;
        dPath += ` L ${y - y0} ${100 - h}`;
      }
      dPath += ` L ${span} 100 Z`;
      const path = document.createElementNS(NS, "path");
      path.setAttribute("d", dPath);
      path.setAttribute("class", "fb-sparkarea");
      svg.appendChild(path);
      this._el.querySelector("#fbSpark").appendChild(svg);
    },

    _wireSlider() {
      const a = this._el.querySelector("#fbY0");
      const b = this._el.querySelector("#fbY1");
      const clamp = () => {
        let lo = +a.value, hi = +b.value;
        if (lo > hi) { const t = lo; lo = hi; hi = t; }   // handles may cross
        this.state.y0 = lo; this.state.y1 = hi;
        this._syncSlider();
      };
      for (const inp of [a, b]) {
        inp.addEventListener("input", () => { clamp(); this._updateSummary(); });
        inp.addEventListener("change", () => { clamp(); this._fire(); });
      }
      this._syncSlider();
    },

    // paint the selected span on the track + dim the excluded sparkline
    _syncSlider() {
      const m = this._meta;
      const span = m.year_max - m.year_min;
      const l = ((this.state.y0 - m.year_min) / span) * 100;
      const r = ((this.state.y1 - m.year_min) / span) * 100;
      const sel = this._el.querySelector("#fbSel");
      sel.style.left = l + "%";
      sel.style.width = Math.max(0, r - l) + "%";
      const spark = this._el.querySelector("#fbSpark");
      spark.style.setProperty("--fb-l", l + "%");
      spark.style.setProperty("--fb-r", r + "%");
      this._el.querySelector("#fbRange").textContent =
        `${this.state.y0}–${this.state.y1}`;
    },

    _updateSummary() {
      const s = this._el.querySelector("#fbSummary");
      if (!s) return;
      const nj = this.state.journals.size, tot = this._allJournals.length;
      if (this.isDefault()) { s.textContent = "all journals · all years"; s.classList.remove("on"); return; }

      // if the selection is exactly one or more whole field groups, say so by
      // name — "Classics only" reads better than "3 of 10 journals"
      let jtxt;
      if (nj === tot) {
        jtxt = "all journals";
      } else if (nj === 0) {
        jtxt = "no journals";
      } else {
        const keys = this._groups ? Object.keys(this._groups.groups) : [];
        const whole = [], broken = [];
        for (const k of keys) {
          const js = this._groupJournals(k);
          if (!js.length) continue;
          const n = js.filter(j => this.state.journals.has(j)).length;
          if (n === js.length) whole.push(this._groups.groups[k].label);
          else if (n > 0) broken.push(k);
        }
        const covered = whole.reduce((a, lab) => {
          const k = keys.find(x => this._groups.groups[x].label === lab);
          return a + this._groupJournals(k).length;
        }, 0);
        jtxt = (whole.length && !broken.length && covered === nj)
          ? whole.join(" + ") + " only"
          : `${nj} of ${tot} journals`;
      }
      s.textContent = jtxt + " · " + this.state.y0 + "–" + this.state.y1;
      s.classList.add("on");
    }
  };

  global.FilterBar = FilterBar;
})(window);
